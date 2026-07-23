"""GT persona-nivel de SHEL5K: has_helmet viene GRATIS de las clases compuestas.

person_with_helmet -> has_helmet=true; person_no_helmet -> has_helmet=false
(violador CR-01). Los 8 labels `person` sueltos (ruido de anotación, doc 66
§B4 del repo docs) se descartan: no tienen atributo confiable. has_vest no
existe en SHEL5K -> false-ausente NO: se omite el campo (el dataset no lo
anota; un false diría "violador CR-02" y sería fabricado).
"""
import xml.etree.ElementTree as ET

from bench.build_person_gt_shel5k import records_from_xml

_XML = """<annotation>
  <filename>hard_hat_workers0.png</filename>
  <object><name>person_with_helmet</name>
    <bndbox><xmin>10</xmin><ymin>20</ymin><xmax>110</xmax><ymax>220</ymax></bndbox></object>
  <object><name>person_no_helmet</name>
    <bndbox><xmin>200</xmin><ymin>30</ymin><xmax>280</xmax><ymax>210</ymax></bndbox></object>
  <object><name>person</name>
    <bndbox><xmin>1</xmin><ymin>1</ymin><xmax>5</xmax><ymax>5</ymax></bndbox></object>
  <object><name>helmet</name>
    <bndbox><xmin>30</xmin><ymin>20</ymin><xmax>60</xmax><ymax>45</ymax></bndbox></object>
</annotation>"""


def test_records_desde_clases_compuestas():
    recs = records_from_xml(ET.fromstring(_XML), "ruta/imgs/hard_hat_workers0.png")
    assert len(recs) == 2, "los `person` sueltos se descartan"
    with_h = next(r for r in recs if r["has_helmet"])
    no_h = next(r for r in recs if not r["has_helmet"])
    assert with_h["person_bbox"] == [10.0, 20.0, 110.0, 220.0]
    assert no_h["person_bbox"] == [200.0, 30.0, 280.0, 210.0]
    assert all(r["file_name"] == "ruta/imgs/hard_hat_workers0.png" for r in recs)
    assert all("has_vest" not in r for r in recs), "has_vest no se fabrica"
