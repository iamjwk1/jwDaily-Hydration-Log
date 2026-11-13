"""Self-contained, offline XLSX liquid pictograms (PNG + DrawingML).

No external fonts, URLs, Pillow, network access, or Home Assistant dependencies.
Pictograms are intentionally simplified symbolic previews, not exact MDI artwork.
"""
from __future__ import annotations

from math import sqrt
from struct import pack
from xml.sax.saxutils import escape
import zlib


def _chunk(tag, data):
    return pack(">I",len(data))+tag+data+pack(">I",zlib.crc32(tag+data)&0xffffffff)


def _polygon(x, y, pts):
    inside=False
    j=len(pts)-1
    for i in range(len(pts)):
        xi, yi=pts[i];xj,yj=pts[j]
        if (yi>y)!=(yj>y) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
            inside=not inside
        j=i
    return inside


def png_icon(icon_mdi, color="#5795CE", size=48):
    if not 24<=size<=128:
        raise ValueError("Invalid pictogram size")
    raw=color.lstrip("#")
    try:
        rgb=tuple(bytes.fromhex(raw))
        if len(rgb)!=3:raise ValueError
    except (ValueError,TypeError):
        rgb=(87,149,206)
    kind=str(icon_mdi or "").lower()
    if "coffee" in kind or "tea" in kind:mode="cup"
    elif "wine" in kind:mode="wine"
    elif "soup" in kind or "bowl" in kind:mode="soup"
    elif "milk" in kind:mode="bottle"
    elif "water" in kind or "drop" in kind:mode="drop"
    else:mode="glass"
    rows=bytearray()
    for iy in range(size):
        rows.append(0)
        for ix in range(size):
            x=(ix+0.5)*48/size;y=(iy+0.5)*48/size
            circle=(x-24)**2+(y-24)**2<=21**2
            if not circle:
                rows.extend((0,0,0,0));continue
            white=False
            if mode=="drop":
                white=(_polygon(x,y,[(24,8),(14,22),(12,29),(15,36),(20,39),(28,39),(33,35),(36,29),(34,23)])
                       or ((x-24)**2+(y-29)**2<10**2 and y>=26))
            elif mode=="cup":
                white=(13<=x<=31 and 19<=y<=33 and (y<=29 or 15<=x<=29)
                       or (31<=x<=38 and 21<=y<=29 and 3**2<=(x-33)**2+(y-25)**2<=7**2)
                       or (15<=x<=17 and 9<=y<=17 and int(y)%4!=0)
                       or (23<=x<=25 and 9<=y<=17 and int(y)%4!=0))
            elif mode=="wine":
                white=(_polygon(x,y,[(14,12),(34,12),(32,21),(28,27),(20,27),(16,21)])
                       or 22<=x<=26 and 26<=y<=38
                       or 16<=x<=32 and 37<=y<=40)
            elif mode=="soup":
                white=(_polygon(x,y,[(11,23),(37,23),(33,34),(28,38),(20,38),(15,34)])
                       or 12<=x<=36 and 20<=y<=23)
            elif mode=="bottle":
                white=(18<=x<=30 and 16<=y<=37
                       or 21<=x<=27 and 10<=y<=17
                       or 19<=x<=29 and 36<=y<=40)
            else:
                white=(15<=x<=33 and 17<=y<=37 and
                       (x>=16+(y-17)*0.04 and x<=32-(y-17)*0.04)
                       or 24<=x<=27 and 9<=y<=22)
            rows.extend((255,255,255,255) if white else (*rgb,255))
    raw_png=(b"\x89PNG\r\n\x1a\n"+_chunk(b"IHDR",pack(">IIBBBBB",size,size,8,6,0,0,0))
             +_chunk(b"IDAT",zlib.compress(bytes(rows),9))+_chunk(b"IEND",b""))
    return raw_png


def drawing_parts(rows):
    """Rows: iterable of (Excel row number, MDI icon name, #RRGGBB color)."""
    anchors=[]
    images=[]
    for n,(row,mdi,color) in enumerate(rows,1):
        images.append(png_icon(mdi,color))
        # Exact cell E(row), using 34px square inside the 44pt row.
        anchors.append(
            '<xdr:oneCellAnchor><xdr:from>'
            f'<xdr:col>4</xdr:col><xdr:colOff>24000</xdr:colOff>'
            f'<xdr:row>{row-1}</xdr:row><xdr:rowOff>24000</xdr:rowOff>'
            '</xdr:from><xdr:ext cx="323850" cy="323850"/>'
            '<xdr:pic><xdr:nvPicPr>'
            f'<xdr:cNvPr id="{n}" name="Liquid icon {n}"/>'
            '<xdr:cNvPicPr/></xdr:nvPicPr>'
            '<xdr:blipFill><a:blip r:embed="rId'+str(n)+'"/>'
            '<a:stretch><a:fillRect/></a:stretch></xdr:blipFill>'
            '<xdr:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="323850" cy="323850"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>'
            '</xdr:pic><xdr:clientData/></xdr:oneCellAnchor>')
    if not images:
        return b"",b"",[]
    drawing=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" '
             'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
             'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
             +''.join(anchors)+'</xdr:wsDr>').encode()
    rels=('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          +''.join(f'<Relationship Id="rId{n}" '
                   'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                   f'Target="../media/liquid{n}.png"/>' for n in range(1,len(images)+1))
          +'</Relationships>').encode()
    return drawing,rels,images
