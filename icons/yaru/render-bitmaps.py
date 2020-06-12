#!/usr/bin/python3
#
# This file has been take from Suru, and modified to just generate cantata icons
#
# ------------8<----------
# Legal Stuff:
#
# This file is part of the Suru Icon Theme and is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free Software
# Foundation; version 3.
#
# This file is part of the Suru Icon Theme and is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <https://www.gnu.org/licenses/lgpl-3.0.txt>
#
#
# Thanks to the GNOME icon developers for the original version of this script
# ------------8<----------
import argparse
import os
import subprocess
import sys
import xml.sax

INKSCAPE = "/usr/bin/inkscape"
OPTIPNG = "/usr/bin/optipng"

# DPI multipliers to render at
DPIS = [1, 2]

inkscape_process = None


def main(SRC):
    def optimize_png(png_file):
        if os.path.exists(OPTIPNG):
            process = subprocess.Popen([OPTIPNG, "-quiet", "-o7", png_file])
            process.wait()

    def wait_for_prompt(process, command=None):
        if command is not None:
            process.stdin.write((command + "\n").encode("utf-8"))

        # This is kinda ugly ...
        # Wait for just a '>', or '\n>' if some other char appearead first
        output = process.stdout.read(1)
        if output == b">":
            return

        output += process.stdout.read(1)
        while output != b"\n>":
            output += process.stdout.read(1)
            output = output[1:]

    def start_inkscape():
        process = subprocess.Popen(
            [INKSCAPE, "--shell"],
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        wait_for_prompt(process)
        return process

    def inkscape_render_rect(icon_file, rect, dpi, output_file):
        global inkscape_process
        if inkscape_process is None:
            inkscape_process = start_inkscape()

        cmd = [
            icon_file, "--export-dpi",
            str(dpi), "-i", rect, "-e", output_file
        ]
        wait_for_prompt(inkscape_process, " ".join(cmd))
        optimize_png(output_file)

    class ContentHandler(xml.sax.ContentHandler):
        ROOT = 0
        SVG = 1
        LAYER = 2
        OTHER = 3
        TEXT = 4

        def __init__(self, path, force=False, filter=None):
            self.stack = [self.ROOT]
            self.inside = [self.ROOT]
            self.path = path
            self.rects = []
            self.state = self.ROOT
            self.chars = ""
            self.force = force
            self.filter = filter

        def endDocument(self):
            pass

        def startElement(self, name, attrs):
            if self.inside[-1] == self.ROOT:
                if name == "svg":
                    self.stack.append(self.SVG)
                    self.inside.append(self.SVG)
                    return
            elif self.inside[-1] == self.SVG:
                if (name == "g" and ("inkscape:groupmode" in attrs)
                        and ("inkscape:label" in attrs)
                        and attrs["inkscape:groupmode"] == "layer"
                        and attrs["inkscape:label"].startswith("Baseplate")):
                    self.stack.append(self.LAYER)
                    self.inside.append(self.LAYER)
                    self.context = None
                    self.icon_name = None
                    self.rects = []
                    return
            elif self.inside[-1] == self.LAYER:
                if (name == "text" and ("inkscape:label" in attrs)
                        and attrs["inkscape:label"] == "context"):
                    self.stack.append(self.TEXT)
                    self.inside.append(self.TEXT)
                    self.text = "context"
                    self.chars = ""
                    return
                elif (name == "text" and ("inkscape:label" in attrs)
                      and attrs["inkscape:label"] == "icon-name"):
                    self.stack.append(self.TEXT)
                    self.inside.append(self.TEXT)
                    self.text = "icon-name"
                    self.chars = ""
                    return
                elif name == "rect":
                    self.rects.append(attrs)

            self.stack.append(self.OTHER)

        def endElement(self, name):
            stacked = self.stack.pop()
            if self.inside[-1] == stacked:
                self.inside.pop()

            if stacked == self.TEXT and self.text is not None:
                assert self.text in ["context", "icon-name"]
                if self.text == "context":
                    self.context = self.chars
                elif self.text == "icon-name":
                    self.icon_name = self.chars
                self.text = None
            elif stacked == self.LAYER:
                assert self.icon_name
                assert self.context

                if self.filter is not None and self.icon_name not in self.filter:
                    return

                print(self.context, self.icon_name)
                for rect in self.rects:
                    for dpi_factor in DPIS:
                        width = rect["width"]
                        height = rect["height"]
                        id = rect["id"]
                        dpi = 96 * dpi_factor

                        size_str = "%sx%s" % (width, height)
                        if dpi_factor != 1:
                            size_str += "@%sx" % dpi_factor

                        outfile = self.icon_name + "-" + size_str + ".png"
                        # Do a time based check!
                        if self.force or not os.path.exists(outfile):
                            inkscape_render_rect(self.path, id, dpi, outfile)
                            sys.stdout.write(".")
                        else:
                            stat_in = os.stat(self.path)
                            stat_out = os.stat(outfile)
                            if stat_in.st_mtime > stat_out.st_mtime:
                                inkscape_render_rect(self.path, id, dpi,
                                                     outfile)
                                sys.stdout.write(".")
                            else:
                                sys.stdout.write("-")
                        sys.stdout.flush()
                sys.stdout.write("\n")
                sys.stdout.flush()

        def characters(self, chars):
            self.chars += chars.strip()

    print("")
    print("Rendering from SVGs in", SRC)
    print("")
    for file in os.listdir(SRC):
        if file[-4:] == ".svg":
            file = os.path.join(SRC, file)
            handler = ContentHandler(file)
            xml.sax.parse(open(file), handler)
    print("")


main(".")
