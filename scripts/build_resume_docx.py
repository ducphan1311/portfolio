#!/usr/bin/env python3
"""Build the editable, Word-native resume used by the portfolio download."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CP_NS = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

ET.register_namespace("w", W_NS)
ET.register_namespace("r", R_NS)
ET.register_namespace("cp", CP_NS)
ET.register_namespace("dc", DC_NS)
ET.register_namespace("dcterms", DCTERMS_NS)
ET.register_namespace("xsi", XSI_NS)


def qn(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


W = lambda name: qn(W_NS, name)
R = lambda name: qn(R_NS, name)


NAVY = "123F63"
BLUE = "0878B8"
INK = "152334"
MUTED = "5E6A78"
LINE = "D8E2E9"
SKY = "EAF5FB"
PALE = "F6F9FB"
WHITE = "FFFFFF"


class DocumentBuilder:
    def __init__(self) -> None:
        self.document = ET.Element(W("document"))
        self.body = ET.SubElement(self.document, W("body"))
        self.hyperlinks: list[tuple[str, str]] = []

    def add_hyperlink_relationship(self, target: str) -> str:
        relationship_id = f"rId{10 + len(self.hyperlinks)}"
        self.hyperlinks.append((relationship_id, target))
        return relationship_id

    @staticmethod
    def set_cell_margins(
        cell_properties: ET.Element,
        *,
        top: int = 90,
        right: int = 120,
        bottom: int = 90,
        left: int = 120,
    ) -> None:
        margins = ET.SubElement(cell_properties, W("tcMar"))
        for edge, value in (
            ("top", top),
            ("right", right),
            ("bottom", bottom),
            ("left", left),
        ):
            ET.SubElement(
                margins,
                W(edge),
                {W("w"): str(value), W("type"): "dxa"},
            )

    @staticmethod
    def add_borders(
        parent_properties: ET.Element,
        tag: str,
        *,
        color: str = LINE,
        size: int = 6,
        left_color: str | None = None,
        left_size: int | None = None,
        inside: bool = True,
    ) -> None:
        borders = ET.SubElement(parent_properties, W(tag))
        for edge in ("top", "left", "bottom", "right"):
            edge_color = left_color if edge == "left" and left_color else color
            edge_size = left_size if edge == "left" and left_size else size
            ET.SubElement(
                borders,
                W(edge),
                {
                    W("val"): "single",
                    W("sz"): str(edge_size),
                    W("space"): "0",
                    W("color"): edge_color,
                },
            )
        if inside:
            for edge in ("insideH", "insideV"):
                ET.SubElement(
                    borders,
                    W(edge),
                    {
                        W("val"): "single",
                        W("sz"): str(size),
                        W("space"): "0",
                        W("color"): color,
                    },
                )

    def paragraph(
        self,
        parent: ET.Element,
        text: str = "",
        *,
        size: int = 18,
        bold: bool = False,
        italic: bool = False,
        color: str = INK,
        align: str | None = None,
        before: int = 0,
        after: int = 60,
        line: int = 240,
        keep_next: bool = False,
        keep_lines: bool = False,
        uppercase_spacing: int | None = None,
        border_bottom: tuple[str, int] | None = None,
        border_left: tuple[str, int] | None = None,
    ) -> ET.Element:
        paragraph = ET.SubElement(parent, W("p"))
        properties = ET.SubElement(paragraph, W("pPr"))
        ET.SubElement(
            properties,
            W("spacing"),
            {
                W("before"): str(before),
                W("after"): str(after),
                W("line"): str(line),
                W("lineRule"): "auto",
            },
        )
        if align:
            ET.SubElement(properties, W("jc"), {W("val"): align})
        if keep_next:
            ET.SubElement(properties, W("keepNext"))
        if keep_lines:
            ET.SubElement(properties, W("keepLines"))
        if border_bottom or border_left:
            borders = ET.SubElement(properties, W("pBdr"))
            if border_bottom:
                ET.SubElement(
                    borders,
                    W("bottom"),
                    {
                        W("val"): "single",
                        W("sz"): str(border_bottom[1]),
                        W("space"): "4",
                        W("color"): border_bottom[0],
                    },
                )
            if border_left:
                ET.SubElement(
                    borders,
                    W("left"),
                    {
                        W("val"): "single",
                        W("sz"): str(border_left[1]),
                        W("space"): "7",
                        W("color"): border_left[0],
                    },
                )
        if text:
            self.run(
                paragraph,
                text,
                size=size,
                bold=bold,
                italic=italic,
                color=color,
                spacing=uppercase_spacing,
            )
        return paragraph

    @staticmethod
    def run(
        paragraph: ET.Element,
        text: str,
        *,
        size: int = 18,
        bold: bool = False,
        italic: bool = False,
        color: str = INK,
        underline: bool = False,
        spacing: int | None = None,
    ) -> ET.Element:
        run = ET.SubElement(paragraph, W("r"))
        properties = ET.SubElement(run, W("rPr"))
        ET.SubElement(
            properties,
            W("rFonts"),
            {
                W("ascii"): "Arial",
                W("hAnsi"): "Arial",
                W("eastAsia"): "Arial",
                W("cs"): "Arial",
            },
        )
        ET.SubElement(properties, W("sz"), {W("val"): str(size)})
        ET.SubElement(properties, W("szCs"), {W("val"): str(size)})
        ET.SubElement(properties, W("color"), {W("val"): color})
        if bold:
            ET.SubElement(properties, W("b"))
        if italic:
            ET.SubElement(properties, W("i"))
        if underline:
            ET.SubElement(properties, W("u"), {W("val"): "single"})
        if spacing is not None:
            ET.SubElement(properties, W("spacing"), {W("val"): str(spacing)})
        node = ET.SubElement(run, W("t"), {qn("http://www.w3.org/XML/1998/namespace", "space"): "preserve"})
        node.text = text
        return run

    def hyperlink(
        self,
        paragraph: ET.Element,
        label: str,
        target: str,
        *,
        size: int = 16,
        bold: bool = False,
        color: str = BLUE,
    ) -> None:
        relationship_id = self.add_hyperlink_relationship(target)
        link = ET.SubElement(paragraph, W("hyperlink"), {R("id"): relationship_id})
        run = ET.SubElement(link, W("r"))
        properties = ET.SubElement(run, W("rPr"))
        ET.SubElement(
            properties,
            W("rFonts"),
            {
                W("ascii"): "Arial",
                W("hAnsi"): "Arial",
                W("eastAsia"): "Arial",
                W("cs"): "Arial",
            },
        )
        ET.SubElement(properties, W("sz"), {W("val"): str(size)})
        ET.SubElement(properties, W("szCs"), {W("val"): str(size)})
        ET.SubElement(properties, W("color"), {W("val"): color})
        ET.SubElement(properties, W("u"), {W("val"): "single"})
        if bold:
            ET.SubElement(properties, W("b"))
        text_node = ET.SubElement(run, W("t"))
        text_node.text = label

    def table(
        self,
        parent: ET.Element,
        widths: list[int],
        *,
        borders: bool = False,
        border_color: str = LINE,
        border_size: int = 5,
        left_accent: str | None = None,
        cell_margin: int = 100,
    ) -> ET.Element:
        table = ET.SubElement(parent, W("tbl"))
        properties = ET.SubElement(table, W("tblPr"))
        ET.SubElement(
            properties,
            W("tblW"),
            {W("w"): str(sum(widths)), W("type"): "dxa"},
        )
        ET.SubElement(properties, W("tblLayout"), {W("type"): "fixed"})
        margins = ET.SubElement(properties, W("tblCellMar"))
        for edge in ("top", "left", "bottom", "right"):
            ET.SubElement(
                margins,
                W(edge),
                {W("w"): str(cell_margin), W("type"): "dxa"},
            )
        table_borders = ET.SubElement(properties, W("tblBorders"))
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            if borders:
                color = left_accent if edge == "left" and left_accent else border_color
                size = 18 if edge == "left" and left_accent else border_size
                attributes = {
                    W("val"): "single",
                    W("sz"): str(size),
                    W("space"): "0",
                    W("color"): color,
                }
            else:
                attributes = {W("val"): "nil"}
            ET.SubElement(table_borders, W(edge), attributes)
        grid = ET.SubElement(table, W("tblGrid"))
        for width in widths:
            ET.SubElement(grid, W("gridCol"), {W("w"): str(width)})
        return table

    @staticmethod
    def row(table: ET.Element, *, cant_split: bool = True) -> ET.Element:
        row = ET.SubElement(table, W("tr"))
        if cant_split:
            properties = ET.SubElement(row, W("trPr"))
            ET.SubElement(properties, W("cantSplit"))
        return row

    def cell(
        self,
        row: ET.Element,
        width: int,
        *,
        fill: str | None = None,
        v_align: str = "top",
        margins: tuple[int, int, int, int] = (100, 120, 100, 120),
        border: bool = False,
        left_accent: str | None = None,
    ) -> ET.Element:
        cell = ET.SubElement(row, W("tc"))
        properties = ET.SubElement(cell, W("tcPr"))
        ET.SubElement(properties, W("tcW"), {W("w"): str(width), W("type"): "dxa"})
        ET.SubElement(properties, W("vAlign"), {W("val"): v_align})
        if fill:
            ET.SubElement(properties, W("shd"), {W("val"): "clear", W("fill"): fill})
        self.set_cell_margins(
            properties,
            top=margins[0],
            right=margins[1],
            bottom=margins[2],
            left=margins[3],
        )
        if border:
            self.add_borders(
                properties,
                "tcBorders",
                color=LINE,
                size=5,
                left_color=left_accent,
                left_size=18,
                inside=False,
            )
        return cell

    def section_heading(self, parent: ET.Element, title: str, *, before: int = 80) -> None:
        self.paragraph(
            parent,
            title.upper(),
            size=21,
            bold=True,
            color=NAVY,
            before=before,
            after=100,
            line=240,
            keep_next=True,
            uppercase_spacing=18,
            border_bottom=(LINE, 7),
        )

    def add_stat(self, cell: ET.Element, value: str, label: str) -> None:
        self.paragraph(cell, value, size=24, bold=True, color=NAVY, after=0, line=240)
        self.paragraph(
            cell,
            label.upper(),
            size=15,
            bold=True,
            color=MUTED,
            after=0,
            line=220,
            uppercase_spacing=8,
        )

    def add_experience(
        self,
        parent: ET.Element,
        role: str,
        company: str,
        date: str,
        details: str,
    ) -> None:
        heading = self.table(parent, [3300, 1750], cell_margin=0)
        heading_row = self.row(heading)
        role_cell = self.cell(heading_row, 3300, margins=(0, 0, 0, 0))
        date_cell = self.cell(heading_row, 1750, margins=(0, 0, 0, 0))
        self.paragraph(
            role_cell,
            role,
            size=20,
            bold=True,
            color=INK,
            after=0,
            line=235,
            keep_next=True,
        )
        self.paragraph(
            date_cell,
            date,
            size=15,
            bold=True,
            color=MUTED,
            align="right",
            after=0,
            line=225,
            keep_next=True,
        )
        self.paragraph(
            parent,
            company,
            size=17,
            bold=True,
            color=BLUE,
            after=5,
            line=225,
            keep_next=True,
        )
        self.paragraph(
            parent,
            details,
            size=17,
            color=MUTED,
            after=115,
            line=250,
            keep_lines=True,
            border_left=(SKY, 10),
        )

    def add_skill(self, parent: ET.Element, title: str, values: str) -> None:
        self.paragraph(
            parent,
            title,
            size=18,
            bold=True,
            color=NAVY,
            after=5,
            line=230,
            keep_next=True,
        )
        self.paragraph(
            parent,
            values,
            size=17,
            color=MUTED,
            after=105,
            line=250,
            keep_lines=True,
        )

    def add_project_card(
        self,
        cell: ET.Element,
        *,
        name: str,
        product_type: str,
        meta: str,
        scope: str,
        technologies: str,
        technology_label: str = "Core",
        date: str | None = None,
        app_store: str | None = None,
        google_play: str | None = None,
    ) -> None:
        if date:
            title_table = self.table(cell, [3300, 1150], cell_margin=0)
            title_row = self.row(title_table)
            title_cell = self.cell(title_row, 3300, margins=(0, 0, 0, 0))
            date_cell = self.cell(title_row, 1150, margins=(0, 0, 0, 0))
            self.paragraph(
                title_cell,
                name,
                size=23,
                bold=True,
                color=NAVY,
                after=0,
                line=245,
                keep_next=True,
            )
            self.paragraph(
                date_cell,
                date,
                size=15,
                bold=True,
                color=MUTED,
                align="right",
                after=0,
                line=225,
            )
        else:
            self.paragraph(
                cell,
                name,
                size=23,
                bold=True,
                color=NAVY,
                after=0,
                line=245,
                keep_next=True,
            )
        self.paragraph(
            cell,
            product_type,
            size=17,
            color=MUTED,
            after=75,
            line=235,
            keep_next=True,
        )
        meta_table = self.table(cell, [4450], cell_margin=55)
        meta_row = self.row(meta_table)
        meta_cell = self.cell(meta_row, 4450, fill=SKY, margins=(55, 85, 55, 85))
        self.paragraph(
            meta_cell,
            meta,
            size=16,
            bold=True,
            color=NAVY,
            after=0,
            line=225,
            keep_next=True,
        )
        self.paragraph(
            cell,
            scope,
            size=17,
            color=INK,
            after=75,
            line=250,
            keep_lines=True,
        )
        technology_line = self.paragraph(
            cell,
            "",
            size=16,
            color=MUTED,
            after=40 if app_store or google_play else 0,
            line=225,
        )
        self.run(technology_line, f"{technology_label}: ", size=16, bold=True, color=NAVY)
        self.run(technology_line, technologies, size=16, color=MUTED)
        if app_store or google_play:
            links = self.paragraph(cell, "", size=16, after=0, line=225)
            if app_store:
                self.hyperlink(links, "App Store", app_store, size=16, bold=True)
            if app_store and google_play:
                self.run(links, "  ·  ", size=16, color=MUTED)
            if google_play:
                self.hyperlink(links, "Google Play", google_play, size=16, bold=True)

    def add_compact_project(
        self,
        cell: ET.Element,
        name: str,
        details: str,
    ) -> None:
        self.paragraph(
            cell,
            name,
            size=19,
            bold=True,
            color=NAVY,
            after=4,
            line=230,
            keep_next=True,
        )
        self.paragraph(
            cell,
            details,
            size=16,
            color=MUTED,
            after=0,
            line=235,
            keep_lines=True,
        )

    def page_break(self) -> None:
        paragraph = self.paragraph(self.body, "", after=0, line=20)
        run = ET.SubElement(paragraph, W("r"))
        ET.SubElement(run, W("br"), {W("type"): "page"})

    def finish(self) -> None:
        section = ET.SubElement(self.body, W("sectPr"))
        ET.SubElement(section, W("pgSz"), {W("w"): "11906", W("h"): "16838"})
        ET.SubElement(
            section,
            W("pgMar"),
            {
                W("top"): "650",
                W("right"): "850",
                W("bottom"): "650",
                W("left"): "850",
                W("header"): "300",
                W("footer"): "300",
                W("gutter"): "0",
            },
        )


def build_document() -> DocumentBuilder:
    builder = DocumentBuilder()
    body = builder.body

    header = builder.table(body, [6200, 4006], borders=False, cell_margin=0)
    header_properties = header.find(W("tblPr"))
    existing_borders = header_properties.find(W("tblBorders"))
    if existing_borders is not None:
        header_properties.remove(existing_borders)
    top_border = ET.SubElement(header_properties, W("tblBorders"))
    for edge in ("left", "bottom", "right", "insideH", "insideV"):
        ET.SubElement(top_border, W(edge), {W("val"): "nil"})
    ET.SubElement(
        top_border,
        W("top"),
        {W("val"): "single", W("sz"): "28", W("space"): "0", W("color"): NAVY},
    )
    header_row = builder.row(header)
    identity = builder.cell(header_row, 6200, margins=(130, 0, 100, 0))
    contact = builder.cell(header_row, 4006, margins=(130, 0, 100, 120))
    builder.paragraph(
        identity,
        "MOBILE ENGINEERING · PRODUCT DELIVERY",
        size=15,
        bold=True,
        color=BLUE,
        after=45,
        line=220,
        uppercase_spacing=18,
    )
    builder.paragraph(
        identity,
        "Phan Minh Duc",
        size=50,
        bold=True,
        color=NAVY,
        after=20,
        line=300,
    )
    builder.paragraph(
        identity,
        "Mobile Software Engineer & Team Lead",
        size=24,
        bold=True,
        color=MUTED,
        after=0,
        line=245,
    )
    contact_lines = [
        ("Phone", "+84 395 828 955", "tel:+84395828955"),
        ("Email", "ducphan1311@gmail.com", "mailto:ducphan1311@gmail.com"),
        ("GitHub", "github.com/ducphan1311", "https://github.com/ducphan1311"),
    ]
    for label, value, target in contact_lines:
        line = builder.paragraph(
            contact,
            "",
            size=16,
            align="right",
            after=15,
            line=225,
        )
        builder.run(line, f"{label.upper()}  ", size=14, bold=True, color=NAVY)
        builder.hyperlink(line, value, target, size=16, color=MUTED)
    location = builder.paragraph(contact, "", align="right", after=0, line=225)
    builder.run(location, "BASED IN  ", size=14, bold=True, color=NAVY)
    builder.run(location, "Ha Noi, Vietnam", size=16, color=MUTED)

    builder.section_heading(body, "Profile", before=80)
    builder.paragraph(
        body,
        (
            "Mobile engineer with 6 years delivering iOS and Android products across "
            "banking, fintech, healthcare, e-commerce, and education. Flutter specialist "
            "with native Kotlin/Swift experience, end-to-end ownership, and team leadership. "
            "Shipped 10+ mobile apps across multiple product domains."
        ),
        size=18,
        color=INK,
        after=115,
        line=255,
        keep_lines=True,
    )

    stats = builder.table(body, [2551, 2551, 2551, 2553], borders=True, border_color=WHITE, border_size=12)
    stats_row = builder.row(stats)
    for width, value, label in (
        (2551, "6 years", "Experience"),
        (2551, "10+ apps", "Published"),
        (2551, "iOS + Android", "Platforms"),
        (2553, "Lead + IC", "Delivery roles"),
    ):
        stat_cell = builder.cell(stats_row, width, fill=SKY, margins=(100, 130, 100, 130))
        builder.add_stat(stat_cell, value, label)

    main_layout = builder.table(body, [6200, 4006], cell_margin=0)
    main_row = builder.row(main_layout, cant_split=False)
    experience = builder.cell(main_row, 6200, margins=(80, 240, 0, 0))
    skills = builder.cell(main_row, 4006, fill=PALE, margins=(80, 180, 80, 180))
    builder.section_heading(experience, "Experience", before=30)
    for role in (
        (
            "Software Engineer",
            "VPBank",
            "Jul 2025 — Present",
            "Mobile development across Flutter, Android/Kotlin, and iOS/Swift.",
        ),
        (
            "Mobile Team Lead",
            "BSM Labs",
            "Feb 2025 — Jul 2025",
            "Led planning, code review, delivery, optimization, and maintenance.",
        ),
        (
            "Mobile Team Lead",
            "Ohmidas VN",
            "Sep 2023 — Feb 2025",
            "Led Flutter products and collaborated across Java, Python, and PostgreSQL.",
        ),
        (
            "Software Engineer",
            "GROOO International",
            "Aug 2022 — Sep 2023",
            "Developed and maintained Flutter and React Native applications.",
        ),
        (
            "Software Engineer",
            "AgileTech",
            "Feb 2021 — Jul 2022",
            "Delivered mobile commerce features with Flutter and React Native.",
        ),
        (
            "Software Engineer",
            "VTD",
            "Sep 2020 — Feb 2021",
            "Built native Android functionality with Kotlin.",
        ),
    ):
        builder.add_experience(experience, *role)
    builder.paragraph(experience, "", size=2, after=0, line=20)

    builder.section_heading(skills, "Core Skills", before=30)
    for title, values in (
        ("Mobile", "Flutter · React Native · Android/Kotlin · iOS/Swift"),
        ("Backend & Data", "Java · Python · PHP · PostgreSQL · Firebase · MySQL · SQLite · Hive"),
        ("Delivery & Tooling", "Team planning · Code review · Docker · Git · GitHub · Azure · Bitbucket"),
        ("Languages", "Vietnamese — Native · English — B2, reading & writing"),
    ):
        builder.add_skill(skills, title, values)
    builder.section_heading(skills, "Education", before=65)
    builder.paragraph(
        skills,
        "Electric Power University",
        size=18,
        bold=True,
        color=NAVY,
        after=5,
        line=230,
    )
    builder.paragraph(
        skills,
        "Information Technology · 2017–2022",
        size=17,
        color=MUTED,
        after=65,
        line=235,
    )
    builder.paragraph(
        skills,
        "ITPlus Academy · 2020–2021",
        size=16,
        color=MUTED,
        after=15,
        line=230,
    )
    builder.paragraph(
        skills,
        "English B2 CEFR · 2021",
        size=16,
        color=MUTED,
        after=0,
        line=230,
    )

    builder.section_heading(body, "Project Experience", before=110)
    banking = builder.table(body, [5020, 160, 5026], cell_margin=0)
    banking_row = builder.row(banking)
    gpbank = builder.cell(
        banking_row,
        5020,
        fill=WHITE,
        margins=(120, 150, 120, 170),
        border=True,
        left_accent=BLUE,
    )
    spacer = builder.cell(banking_row, 160, margins=(0, 0, 0, 0))
    builder.paragraph(spacer, "", size=2, after=0, line=20)
    neobiz = builder.cell(
        banking_row,
        5026,
        fill=WHITE,
        margins=(120, 150, 120, 170),
        border=True,
        left_accent=BLUE,
    )
    builder.add_project_card(
        gpbank,
        name="GPBank Biz",
        product_type="Corporate Digital Banking Mobile App · Associated with VPBank",
        meta="Project team ≈10  ·  Mobile team 1  ·  Sole Mobile Engineer",
        scope="Owned the iOS and Android app end-to-end, from initial development through handover and maintenance.",
        technologies="iOS · Android",
        technology_label="Platforms",
        date="Current",
        app_store="https://apps.apple.com/us/app/gpbank-biz/id6760635421?l=vi",
        google_play="https://play.google.com/store/apps/details?id=com.gpbank.cmbapp&hl=gsw&pli=1",
    )
    builder.add_project_card(
        neobiz,
        name="VPBank NeoBiz Plus",
        product_type="Digital banking for businesses",
        meta="Project team 20  ·  Mobile team 6  ·  Mobile Developer",
        scope="Developed deposit, reporting, and secure authentication features; contributed to additional app modules.",
        technologies="Flutter · iOS/Swift",
        date="2025",
        app_store="https://apps.apple.com/vn/app/vpbank-neobiz-plus/id1659613560",
        google_play="https://play.google.com/store/apps/details?id=com.vpbank.mobileappcmp&hl=vi",
    )

    builder.page_break()

    builder.paragraph(
        body,
        "PROJECT EXPERIENCE · CONTINUED",
        size=15,
        bold=True,
        color=BLUE,
        after=40,
        line=220,
        uppercase_spacing=20,
    )
    builder.paragraph(
        body,
        "Mobile Applications",
        size=34,
        bold=True,
        color=NAVY,
        after=15,
        line=260,
    )
    builder.paragraph(
        body,
        "Fintech, healthcare, education, e-commerce, and additional product experience",
        size=18,
        color=MUTED,
        after=100,
        line=245,
    )
    builder.section_heading(body, "Mobile Projects", before=0)

    projects = [
        {
            "name": "Finavi",
            "product_type": "Fintech & investment application",
            "meta": "Project team 50  ·  Mobile team 7  ·  Mobile Developer",
            "scope": "Built data-visualization charts, the UI-focused Home experience, and interactive Explore & Community features.",
            "technologies": "Flutter · React Native",
            "date": "2022–2023",
            "app_store": "https://apps.apple.com/vn/app/finavi/id6446972800?l=vi",
            "google_play": "https://play.google.com/store/apps/details?id=vn.com.finavi.mts&hl=en-VN",
        },
        {
            "name": "HMUH AI",
            "product_type": "AI-enabled healthcare application",
            "meta": "Project team 10  ·  Mobile team 3  ·  Team Lead / Developer",
            "scope": "Led end-to-end mobile delivery, including planning, feature development, code review, optimization, and maintenance.",
            "technologies": "Flutter",
            "date": "2025",
            "app_store": "https://apps.apple.com/vn/app/hmuh-ai/id6741954542?l=vi",
            "google_play": "https://play.google.com/store/apps/details?id=com.bsmlabs.hmuh",
        },
        {
            "name": "Mainichi Nihongo",
            "product_type": "Online-to-offline Japanese learning",
            "meta": "Project team 10  ·  Mobile team 3  ·  Mobile Team Lead",
            "scope": "Led end-to-end delivery from planning and implementation through review, optimization, and maintenance.",
            "technologies": "Flutter",
            "date": "2023–2024",
            "app_store": "https://apps.apple.com/vn/app/mainichi-nihongo-v2/id6469684532?l=vi",
            "google_play": "https://play.google.com/store/apps/details?id=com.ohmidas.mainichi.nihongo&hl=en-VN",
        },
        {
            "name": "YODY",
            "product_type": "Fashion e-commerce application",
            "meta": "Project team 20  ·  Mobile team 5  ·  Mobile Developer",
            "scope": "Contributed across the full app, including feature delivery, UI refinement, optimization, and maintenance.",
            "technologies": "Flutter",
            "date": "2021–2022",
            "app_store": "https://apps.apple.com/vn/app/yody/id1610704200?l=vi",
            "google_play": "https://play.google.com/store/apps/details?id=com.yody.fashion&hl=en-US",
        },
    ]
    project_table = builder.table(body, [5020, 160, 5026], cell_margin=0)
    for row_index in range(2):
        project_row = builder.row(project_table)
        for column_index in range(3):
            if column_index == 1:
                gap = builder.cell(project_row, 160, margins=(0, 0, 0, 0))
                builder.paragraph(gap, "", size=2, after=0, line=20)
                continue
            project_index = row_index * 2 + (0 if column_index == 0 else 1)
            card = builder.cell(
                project_row,
                5020 if column_index == 0 else 5026,
                fill=WHITE,
                margins=(115, 145, 115, 170),
                border=True,
                left_accent=BLUE,
            )
            builder.add_project_card(card, **projects[project_index])

    builder.section_heading(body, "Additional Projects", before=110)
    other = builder.table(body, [5020, 160, 5026], cell_margin=0)
    other_projects = [
        (
            "Việt Nam Diệu Sử",
            "2025 · Team Lead / Mobile Developer · AR travel · Flutter, iOS/Swift · Team 5",
        ),
        (
            "Ebond",
            "2024–2025 · Team Lead · POS technology research · Flutter, Java, Kafka, .NET · Team 25",
        ),
        (
            "ACCS",
            "2022 · Mobile Developer · Restaurant operations & surveillance · Flutter · Team 10",
        ),
        (
            "Tan Viet Book",
            "2021–2022 · Mobile Developer · E-commerce · Flutter · Team 10",
        ),
    ]
    for row_index in range(2):
        other_row = builder.row(other)
        for column_index in range(3):
            if column_index == 1:
                gap = builder.cell(other_row, 160, margins=(0, 0, 0, 0))
                builder.paragraph(gap, "", size=2, after=0, line=20)
                continue
            project_index = row_index * 2 + (0 if column_index == 0 else 1)
            compact = builder.cell(
                other_row,
                5020 if column_index == 0 else 5026,
                fill=PALE,
                margins=(90, 130, 90, 130),
                border=True,
                left_accent=LINE,
            )
            builder.add_compact_project(compact, *other_projects[project_index])

    note = builder.paragraph(
        body,
        "",
        size=16,
        color=MUTED,
        before=95,
        after=45,
        line=235,
    )
    builder.run(note, "Delivery approach: ", size=16, bold=True, color=NAVY)
    builder.run(
        note,
        "comfortable as both an individual contributor and a mobile lead—from planning and implementation through review, release support, optimization, and maintenance.",
        size=16,
        color=MUTED,
    )
    footer = builder.paragraph(
        body,
        "",
        size=14,
        color=MUTED,
        align="center",
        before=45,
        after=0,
        line=220,
        border_bottom=(LINE, 6),
    )
    builder.run(footer, "ducphan1311@gmail.com  ·  +84 395 828 955", size=14, bold=True, color=MUTED)
    builder.finish()
    return builder


def build_styles() -> bytes:
    styles = ET.Element(W("styles"))
    defaults = ET.SubElement(styles, W("docDefaults"))
    run_defaults = ET.SubElement(defaults, W("rPrDefault"))
    run_properties = ET.SubElement(run_defaults, W("rPr"))
    ET.SubElement(
        run_properties,
        W("rFonts"),
        {
            W("ascii"): "Arial",
            W("hAnsi"): "Arial",
            W("eastAsia"): "Arial",
            W("cs"): "Arial",
        },
    )
    ET.SubElement(run_properties, W("sz"), {W("val"): "18"})
    ET.SubElement(run_properties, W("szCs"), {W("val"): "18"})
    paragraph_defaults = ET.SubElement(defaults, W("pPrDefault"))
    paragraph_properties = ET.SubElement(paragraph_defaults, W("pPr"))
    ET.SubElement(
        paragraph_properties,
        W("spacing"),
        {W("after"): "60", W("line"): "220", W("lineRule"): "auto"},
    )
    normal = ET.SubElement(
        styles,
        W("style"),
        {W("type"): "paragraph", W("default"): "1", W("styleId"): "Normal"},
    )
    ET.SubElement(normal, W("name"), {W("val"): "Normal"})
    ET.SubElement(normal, W("qFormat"))
    return ET.tostring(styles, encoding="utf-8", xml_declaration=True)


def build_relationships(builder: DocumentBuilder) -> bytes:
    relationships = ET.Element("Relationships", xmlns=REL_NS)
    ET.SubElement(
        relationships,
        "Relationship",
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )
    for relationship_id, target in builder.hyperlinks:
        ET.SubElement(
            relationships,
            "Relationship",
            {
                "Id": relationship_id,
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                "Target": target,
                "TargetMode": "External",
            },
        )
    return ET.tostring(relationships, encoding="utf-8", xml_declaration=True)


def build_package(output: Path) -> None:
    builder = build_document()
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""
    root_relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    core_properties = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="{CP_NS}" xmlns:dc="{DC_NS}" xmlns:dcterms="{DCTERMS_NS}" xmlns:xsi="{XSI_NS}">
  <dc:title>Phan Minh Duc — Mobile Software Engineer</dc:title>
  <dc:creator>Phan Minh Duc</dc:creator>
  <dc:subject>Mobile Software Engineer Resume</dc:subject>
  <dc:description>Editable resume with selected mobile product highlights.</dc:description>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
"""
    app_properties = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Microsoft Office Word</Application>
  <AppVersion>16.0000</AppVersion>
</Properties>
"""
    document_xml = ET.tostring(builder.document, encoding="utf-8", xml_declaration=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_relationships)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", build_styles())
        archive.writestr("word/_rels/document.xml.rels", build_relationships(builder))
        archive.writestr("docProps/core.xml", core_properties)
        archive.writestr("docProps/app.xml", app_properties)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "output",
        nargs="?",
        default="Phan_Minh_Duc_Resume.docx",
        type=Path,
    )
    args = parser.parse_args()
    build_package(args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
