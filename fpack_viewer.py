#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------------------------------------------
#   Reflex Font Package Viewer — A tool for viewing the character resources in the data.fpack.
#   Copyright (C) 2026  Daniil Korochansky
#
#   This file is part of Reflex Font Package Viewer.
#
#   Reflex Font Package Viewer is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   Reflex Font Package Viewer is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with Reflex Font Package Viewer.  If not, see <https://www.gnu.org/licenses/>.
# -------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

import struct
from pathlib import Path

import wx
from PIL import Image


ROOT = struct.Struct("<5I")
FONT = struct.Struct("<8I")
GLYPH = struct.Struct("<III2B3b3B")


def raster_size(width: int, height: int) -> int:
    return ((width + 1) // 2) * height


def unpack_mask(raw: bytes, width: int, height: int) -> Image.Image:
    stride = (width + 1) // 2
    if len(raw) != stride * height:
        raise ValueError("Invalid raster size.")

    values = []
    for y in range(height):
        row = raw[y * stride:(y + 1) * stride]
        row_values = []
        for b in row:
            row_values.append((b & 0x0F) * 17)
            row_values.append(((b >> 4) & 0x0F) * 17)

        # For odd widths the final high nibble is padding. Discard it
        # at the end of EVERY row, exactly like the verified CLI extractor.
        values.extend(row_values[:width])

    return Image.frombytes("L", (width, height), bytes(values))


def pack_mask(image: Image.Image, width: int, height: int) -> bytes:
    image = image.convert("L")
    if image.size != (width, height):
        raise ValueError(f"Image must be {width} × {height} pixels.")

    try:
        pixels = list(image.get_flattened_data())
    except AttributeError:
        pixels = list(image.getdata())
    out = bytearray()

    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        for x in range(0, width, 2):
            lo = max(0, min(15, int(round(row[x] / 17.0))))
            hi = 0
            if x + 1 < width:
                hi = max(0, min(15, int(round(row[x + 1] / 17.0))))
            out.append(lo | (hi << 4))

    return bytes(out)


class Glyph:
    def __init__(self, character, p0, p1, width, height):
        self.character = character
        self.p0 = p0
        self.p1 = p1
        self.width = width
        self.height = height

    @property
    def label(self):
        return chr(self.character) if 32 <= self.character < 127 else ""


class FPack:
    def __init__(self, path):
        self.path = Path(path)
        self.data = bytearray(self.path.read_bytes())
        self.fonts = []
        self.parse()

    def parse(self):
        count, _, _, g0, g1 = ROOT.unpack_from(self.data, 0)
        if count != 2:
            raise ValueError("Unsupported FPACK: expected two font groups.")

        for base in (g0, g1):
            _, _, glyph_count, glyph_offset, _, _, _, _ = FONT.unpack_from(
                self.data, base
            )
            table = base + glyph_offset
            glyphs = []

            for i in range(glyph_count):
                off = table + i * GLYPH.size
                ch, p0, p1, w, h, *_ = GLYPH.unpack_from(self.data, off)

                # NUL is an internal record.
                if ch == 0:
                    continue
                if not 32 <= ch <= 126:
                    continue

                glyphs.append(Glyph(ch, p0, p1, w, h))

            self.fonts.append({"base": base, "glyphs": glyphs})

    def read_plane(self, font, glyph, plane):
        offset = glyph.p0 if plane == 0 else glyph.p1
        size = raster_size(glyph.width, glyph.height)
        start = font["base"] + offset
        return unpack_mask(
            bytes(self.data[start:start + size]),
            glyph.width,
            glyph.height,
        )

    def write_plane(self, font, glyph, plane, image):
        offset = glyph.p0 if plane == 0 else glyph.p1
        size = raster_size(glyph.width, glyph.height)
        raw = pack_mask(image, glyph.width, glyph.height)
        if len(raw) != size:
            raise ValueError("Invalid packed raster size.")
        start = font["base"] + offset
        self.data[start:start + size] = raw

    def validate(self):
        for font in self.fonts:
            for glyph in font["glyphs"]:
                size = raster_size(glyph.width, glyph.height)
                if glyph.p1 != glyph.p0 + size:
                    return False
                for offset in (glyph.p0, glyph.p1):
                    start = font["base"] + offset
                    if start < 0 or start + size > len(self.data):
                        return False
        return True

    def save(self, path):
        if not self.validate():
            raise ValueError("The FPACK structure failed validation.")
        Path(path).write_bytes(self.data)


def compose_font1(p0: Image.Image, p1: Image.Image) -> Image.Image:
    """Build the Bike Number glyph from its two stored planes.

    Plane 0 is the visible grayscale/intensity and plane 1 is coverage.
    """
    color = p0.convert("L")
    alpha = p1.convert("L")
    return Image.merge("RGBA", (color, color, color, alpha))


def compose_font0(p0: Image.Image) -> Image.Image:
    """Build Rider Name as grayscale artwork with transparent zero pixels.

    The previous renderer used p0 as alpha and forced RGB to white, which
    destroyed the visible grayscale levels. Here p0 remains the actual
    luminance; only zero-valued background pixels are transparent.
    """
    gray = p0.convert("L")
    alpha = gray.point(lambda v: 0 if v == 0 else 255)
    return Image.merge("RGBA", (gray, gray, gray, alpha))


def quantize_mask(image: Image.Image) -> Image.Image:
    # FPACK stores 16 grayscale levels.
    return image.convert("L").point(
        lambda v: max(0, min(255, int(round(v / 17.0)) * 17))
    )


class Preview(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.image = None
        self.Bind(wx.EVT_PAINT, self.paint)

    def set_image(self, image):
        self.image = image
        self.Refresh()

    def paint(self, _):
        dc = wx.AutoBufferedPaintDC(self)
        dc.SetBackground(wx.Brush(wx.Colour(248, 249, 251)))
        dc.Clear()

        if self.image is None:
            dc.SetTextForeground(wx.Colour(125, 130, 138))
            dc.DrawLabel(
                "Select a character",
                self.GetClientRect(),
                wx.ALIGN_CENTER,
            )
            return

        w, h = self.image.size
        cw, ch = self.GetClientSize()
        scale = min(max(1, (cw - 80) // w), max(1, (ch - 80) // h))
        dw, dh = w * scale, h * scale
        x0, y0 = (cw - dw) // 2, (ch - dh) // 2

        # Always show transparency explicitly. This is especially important
        # for the Rider Number font, whose second plane is the glyph coverage.
        tile = max(4, min(12, scale))
        for yy in range(y0, y0 + dh, tile):
            for xx in range(x0, x0 + dw, tile):
                odd = ((xx - x0) // tile + (yy - y0) // tile) & 1
                c = 238 if odd == 0 else 224
                dc.SetBrush(wx.Brush(wx.Colour(c, c, c)))
                dc.SetPen(wx.TRANSPARENT_PEN)
                dc.DrawRectangle(
                    xx,
                    yy,
                    min(tile, x0 + dw - xx),
                    min(tile, y0 + dh - yy),
                )

        # All user-facing glyphs are rendered as RGBA. Rider Name uses its
        # own grayscale values; Rider Number uses plane 0 as RGB and plane 1
        # as alpha.
        disp = self.image.resize((dw, dh), Image.Resampling.NEAREST).convert("RGBA")
        bmp = wx.Bitmap.FromBufferRGBA(dw, dh, disp.tobytes())
        dc.DrawBitmap(bmp, x0, y0, True)

        dc.SetPen(wx.Pen(wx.Colour(205, 208, 213), 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(x0 - 1, y0 - 1, dw + 2, dh + 2)



class Editor(wx.Frame):
    def __init__(self):
        super().__init__(
            None,
            title="Reflex Font Package Viewer",
            size=(1000, 700),
        )
        self.SetMinSize(wx.Size(1000, 700))
        self.fpack = None
        self.font_index = 0
        self.glyph = None
        self.rendered = None
        self.original = None
        self.modified = False

        self.make_menu()
        self.make_toolbar()
        self.make_ui()
        self.make_status()
        
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_CLOSE, self.close)

    def OnSize(self, event):
        self.Layout()
        self.Refresh()
        event.Skip()

    def make_menu(self):
        bar = wx.MenuBar()

        file_menu = wx.Menu()
        self.open_id = file_menu.Append(wx.ID_OPEN, "Open…\tCtrl+O").GetId()
        self.build_id = file_menu.Append(wx.ID_SAVE, "Build Font Package…\tCtrl+Shift+S").GetId()
        file_menu.AppendSeparator()
        exit_id = file_menu.Append(wx.ID_EXIT, "Exit").GetId()

        char_menu = wx.Menu()
        self.export_id = char_menu.Append(wx.ID_ANY, "Export Character…\tCtrl+E").GetId()
        self.import_id = char_menu.Append(wx.ID_ANY, "Replace Character…\tCtrl+I").GetId()

        help_menu = wx.Menu()
        about_id = help_menu.Append(wx.ID_ABOUT, "About").GetId()

        bar.Append(file_menu, "File")
        bar.Append(char_menu, "Character")
        bar.Append(help_menu, "Help")
        self.SetMenuBar(bar)

        self.Bind(wx.EVT_MENU, self.open_file, id=self.open_id)
        self.Bind(wx.EVT_MENU, self.build_file, id=self.build_id)
        self.Bind(wx.EVT_MENU, self.export_character, id=self.export_id)
        self.Bind(wx.EVT_MENU, self.import_character, id=self.import_id)
        self.Bind(wx.EVT_MENU, self.exit_app, id=exit_id)
        self.Bind(wx.EVT_MENU, self.about, id=about_id)

        self.GetMenuBar().Enable(self.build_id, False)
        self.GetMenuBar().Enable(self.export_id, False)
        self.GetMenuBar().Enable(self.import_id, False)

    def make_toolbar(self):
        self.toolbar = self.CreateToolBar(
            wx.TB_HORIZONTAL | wx.TB_TEXT | wx.TB_FLAT | wx.TB_NODIVIDER
        )
        self.toolbar.SetToolBitmapSize(wx.Size(20, 20))

        self.open_tool = self.toolbar.AddTool(
            wx.ID_OPEN, "Open",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, wx.Size(20, 20)),
            shortHelp="Open data.fpack",
        )
        self.build_tool = self.toolbar.AddTool(
            wx.ID_SAVE, "Build Font Package...",
            wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, wx.Size(20, 20)),
            shortHelp="Build a new data.fpack",
        )
        self.toolbar.AddSeparator()
        self.export_tool = self.toolbar.AddTool(
            wx.ID_ANY, "Export",
            wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN, wx.ART_TOOLBAR, wx.Size(20, 20)),
            shortHelp="Export the selected character",
        )
        self.import_tool = self.toolbar.AddTool(
            wx.ID_ANY, "Import",
            wx.ArtProvider.GetBitmap(wx.ART_GO_UP, wx.ART_TOOLBAR, wx.Size(20, 20)),
            shortHelp="Replace the selected character",
        )
        self.toolbar.Realize()

        self.toolbar.EnableTool(self.build_tool.GetId(), False)
        self.toolbar.EnableTool(self.export_tool.GetId(), False)
        self.toolbar.EnableTool(self.import_tool.GetId(), False)

        self.Bind(wx.EVT_TOOL, self.open_file, id=self.open_tool.GetId())
        self.Bind(wx.EVT_TOOL, self.build_file, id=self.build_tool.GetId())
        self.Bind(wx.EVT_TOOL, self.export_character, id=self.export_tool.GetId())
        self.Bind(wx.EVT_TOOL, self.import_character, id=self.import_tool.GetId())

    def make_ui(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(248, 249, 251))
        root = wx.BoxSizer(wx.VERTICAL)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(panel, label="Font"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)

        self.font_choice = wx.Choice(
            panel,
            choices=["Rider Name", "Rider Number"],
            size=(190, -1),
        )
        self.font_choice.SetSelection(0)
        self.font_choice.Disable()
        top.Add(self.font_choice, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(top, 0, wx.LEFT | wx.TOP, 14)

        split = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        split.SetMinimumPaneSize(260)

        left = wx.Panel(split)
        left.SetBackgroundColour(wx.Colour(248, 249, 251))
        ls = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(left, label="Characters")
        label.SetFont(label.GetFont().Bold())
        ls.Add(label, 0, wx.LEFT | wx.TOP, 12)

        self.list = wx.ListCtrl(
            left,
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_NONE,
        )
        self.list.InsertColumn(0, "Character", width=95)
        self.list.InsertColumn(1, "Size", width=90)
        ls.Add(self.list, 1, wx.EXPAND | wx.ALL, 10)
        left.SetSizer(ls)

        right = wx.Panel(split)
        right.SetBackgroundColour(wx.Colour(248, 249, 251))
        rs = wx.BoxSizer(wx.VERTICAL)

        self.preview = Preview(right)
        rs.Add(self.preview, 1, wx.EXPAND | wx.ALL, 14)

        self.info = wx.StaticText(right, label="Select a character from the list.")
        self.info.SetForegroundColour(wx.Colour(105, 110, 118))
        rs.Add(self.info, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 8)

        help_text = wx.StaticText(
            right,
            label="Export the character, edit the PNG in your preferred graphics editor, then replace it here.",
        )
        help_text.SetForegroundColour(wx.Colour(105, 110, 118))
        help_text.Wrap(540)
        rs.Add(help_text, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)

        right.SetSizer(rs)
        split.SplitVertically(left, right, 300)
        root.Add(split, 1, wx.EXPAND | wx.ALL, 10)
        panel.SetSizer(root)

        self.font_choice.Bind(wx.EVT_CHOICE, self.change_font)
        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.change_glyph)

    def make_status(self):
        status = self.CreateStatusBar(2)
        status.SetStatusWidths([-1, 560])
        status.SetStatusText("Ready", 0)
        status.SetStatusText("No file open", 1)

    def update_actions(self):
        has_file = self.fpack is not None
        has_glyph = self.glyph is not None

        self.font_choice.Enable(has_file)

        self.toolbar.EnableTool(self.build_tool.GetId(), has_file)
        self.toolbar.EnableTool(self.export_tool.GetId(), has_glyph)
        self.toolbar.EnableTool(self.import_tool.GetId(), has_glyph)

        self.GetMenuBar().Enable(self.build_id, has_file)
        self.GetMenuBar().Enable(self.export_id, has_glyph)
        self.GetMenuBar().Enable(self.import_id, has_glyph)

    def file_status(self):
        if not self.fpack:
            self.SetStatusText("No file open", 1)
            return
        value = str(self.fpack.path)
        if self.modified:
            value += "  •  Modified"
        self.SetStatusText(value, 1)

    def open_file(self, _=None):
        dlg = wx.FileDialog(
            self,
            "Open data.fpack",
            wildcard="FPACK files (*.fpack)|*.fpack|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            try:
                f = FPack(dlg.GetPath())
                if not f.validate():
                    raise ValueError("The .fpack file failed validation.")
            except Exception as exc:
                wx.MessageBox(str(exc), "Could not open file", wx.OK | wx.ICON_ERROR)
                return

            self.fpack = f
            self.font_index = 0
            self.modified = False
            self.font_choice.SetSelection(0)
            self.populate()
            self.SetStatusText("File opened", 0)
            self.file_status()
            self.update_actions()
        finally:
            dlg.Destroy()

    def populate(self):
        self.list.DeleteAllItems()
        self.glyph = None
        self.rendered = None
        self.original = None
        self.preview.set_image(None)
        self.info.SetLabel("Select a character from the list.")

        if not self.fpack:
            return

        for g in self.fpack.fonts[self.font_index]["glyphs"]:
            row = self.list.InsertItem(self.list.GetItemCount(), g.label)
            self.list.SetItem(row, 1, f"{g.width} × {g.height}")

        if self.list.GetItemCount():
            self.list.Select(0)
            self.load(0)

    def change_font(self, _):
        self.font_index = self.font_choice.GetSelection()
        self.populate()
        self.update_actions()

    def change_glyph(self, event):
        self.load(event.GetIndex())
        self.update_actions()

    def load(self, index):
        if not self.fpack:
            return
        glyphs = self.fpack.fonts[self.font_index]["glyphs"]
        if not 0 <= index < len(glyphs):
            return

        self.glyph = glyphs[index]
        p0 = self.fpack.read_plane(self.fpack.fonts[self.font_index], self.glyph, 0)

        if self.font_index == 1:
            p1 = self.fpack.read_plane(self.fpack.fonts[self.font_index], self.glyph, 1)
            self.rendered = compose_font1(p0, p1)
        else:
            self.rendered = compose_font0(p0)

        self.original = self.rendered.copy()
        self.preview.set_image(self.rendered)
        self.info.SetLabel(
            f"Character  •  {self.glyph.width} × {self.glyph.height} px"
        )

    def export_character(self, _=None):
        if self.glyph is None or self.rendered is None:
            return

        dlg = wx.FileDialog(
            self,
            "Export Character",
            defaultFile=f"{self.glyph.label}.png",
            wildcard="PNG files (*.png)|*.png",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() == wx.ID_OK:
                # Export the user-facing artwork, never an internal FPACK
                # plane. Rider Name is grayscale + transparent background;
                # Bike Number is RGBA (plane 0 = RGB, plane 1 = alpha).
                self.rendered.save(dlg.GetPath())
                self.SetStatusText("Character exported", 0)
        finally:
            dlg.Destroy()


    def import_character(self, _=None):
        if self.fpack is None or self.glyph is None:
            return

        dlg = wx.FileDialog(
            self,
            "Replace Character",
            wildcard="PNG files (*.png)|*.png",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return

            try:
                source = Image.open(dlg.GetPath())
            except Exception as exc:
                wx.MessageBox(str(exc), "Import failed", wx.OK | wx.ICON_ERROR)
                return

            expected = (self.glyph.width, self.glyph.height)
            if source.size != expected:
                wx.MessageBox(
                    f"The PNG must be {expected[0]} × {expected[1]} pixels.\n"
                    f"Selected image: {source.width} × {source.height} pixels.",
                    "Import failed",
                    wx.OK | wx.ICON_ERROR,
                )
                return

            font = self.fpack.fonts[self.font_index]

            if self.font_index == 0:
                # Rider Name: the exported PNG is grayscale artwork with
                # transparent background. Recover the luminance from RGB;
                # transparent pixels become zero.
                rgba = source.convert("RGBA")
                rgb = rgba.convert("L")
                alpha = rgba.getchannel("A")
                rgb_values = list(rgb.get_flattened_data())
                alpha_values = list(alpha.get_flattened_data())
                values = [
                    v if a > 0 else 0
                    for v, a in zip(rgb_values, alpha_values)
                ]
                image = Image.frombytes(
                    "L",
                    source.size,
                    bytes(values),
                )
                image = quantize_mask(image)
                self.fpack.write_plane(font, self.glyph, 0, image)
                self.rendered = compose_font0(image)
            else:
                # Rider Number:
                #   RGB/luminance -> plane 0 (intensity)
                #   alpha         -> plane 1 (coverage)
                #
                # This is the inverse of compose_font1(), so an unchanged
                # exported PNG round-trips back to the original two planes.
                rgba = source.convert("RGBA")
                rgb = rgba.convert("L")
                alpha = rgba.getchannel("A")

                p0 = quantize_mask(rgb)
                p1 = quantize_mask(alpha)

                self.fpack.write_plane(font, self.glyph, 0, p0)
                self.fpack.write_plane(font, self.glyph, 1, p1)

                self.rendered = Image.merge("RGBA", (p0, p0, p0, p1))

            self.original = self.rendered.copy()
            self.preview.set_image(self.rendered)
            self.modified = True
            self.SetStatusText("Character replaced", 0)
            self.file_status()
            self.update_actions()
        finally:
            dlg.Destroy()


    def build_file(self, _=None):
        if not self.fpack:
            return

        dlg = wx.FileDialog(
            self,
            "Build a new data.fpack",
            defaultFile="data.fpack",
            wildcard="FPACK files (*.fpack)|*.fpack",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        try:
            if dlg.ShowModal() != wx.ID_OK:
                return
            try:
                self.fpack.save(dlg.GetPath())
            except Exception as exc:
                wx.MessageBox(str(exc), "Could not save file", wx.OK | wx.ICON_ERROR)
                return

            self.modified = False
            self.SetStatusText("New data.fpack built", 0)
            self.file_status()
        finally:
            dlg.Destroy()

    def about(self, _):
        wx.MessageBox(
            "Reflex Font Package Viewer\n\n"
            "A tool for viewing the character resources in the data.fpack file for the game MX vs ATV: Reflex.\n\nVersion: 1.0.0\nAuthor: Daniil Korochansky\nLicense: GNU General Public License v3.0",
            "About",
            wx.OK | wx.ICON_INFORMATION,
        )

    def exit_app(self, event):
        self.Close()

    def close(self, event):
        if self.modified:
            result = wx.MessageBox(
                "You have unsaved changes.\n\nExit without saving?",
                "Unsaved changes",
                wx.YES_NO | wx.ICON_WARNING,
            )
            if result != wx.YES:
                event.Veto()
                return
        event.Skip()


class App(wx.App):
    def OnInit(self):
        frame = Editor()
        frame.Centre()
        frame.Show()
        return True


if __name__ == "__main__":
    App(False).MainLoop()
