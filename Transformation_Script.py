import os
import json
import time
import re
import xml.etree.ElementTree as ET
import urllib.parse

# ======================
# HTML CLEANER
# ======================
def clean_primary_html(html_text: str) -> str:
    if not html_text:
        return ""

    cleaned = html_text

    # Remove <ns0:primarytext ...> wrapper
    cleaned = re.sub(r"</?ns0:primarytext[^>]*>", "", cleaned)

    # Replace "html:" prefixes
    cleaned = re.sub(r"<html:([a-zA-Z0-9]+)", r"<\1", cleaned)
    cleaned = re.sub(r"</html:([a-zA-Z0-9]+)>", r"</\1>", cleaned)

    # Remove dir and id attributes
    cleaned = re.sub(r'\s*dir="[^"]*"', "", cleaned)
    cleaned = re.sub(r'\s*id="[^"]*"', "", cleaned)

    # Remove <img> tags
    cleaned = re.sub(r"<img[^>]*>", "", cleaned)

    # Normalize spaces & remove newlines
    cleaned = re.sub(r"\n+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    # Remove empty <p> or <div>
    cleaned = re.sub(r"<p>\s*(?:&nbsp;)?\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<div>\s*(?:&nbsp;)?\s*</div>", "", cleaned, flags=re.IGNORECASE)

    # Fix duplicated inline tags
    cleaned = re.sub(r"<(i|u|b|sub|sup)><\1>", r"<\1>", cleaned)
    cleaned = re.sub(r"</(i|u|b|sub|sup)></\1>", r"</\1>", cleaned)

    # Normalize <table> and <td> styles
    def add_table_styles(match):
        attrs = match.group(1) or ""
        attrs = re.sub(r'width\s*:\s*[^;"]+;?', "", attrs, flags=re.IGNORECASE)
        if "style=" in attrs:
            return f"<table{attrs[:-1]}; width: 70%; border-collapse: collapse; border: 1px solid #696969;\">"
        else:
            return f"<table{attrs} style=\"width: 70%; border-collapse: collapse; border: 1px solid #696969;\">"

    def add_td_styles(match):
        attrs = match.group(1) or ""
        attrs = re.sub(r'width\s*:\s*[^;"]+;?', "", attrs, flags=re.IGNORECASE)
        if "style=" in attrs:
            return f"<td{attrs[:-1]}; border: 1px solid #696969; padding: 4px;\">"
        else:
            return f"<td{attrs} style=\"border: 1px solid #696969; padding: 4px;\">"

    cleaned = re.sub(r"<table([^>]*)>", add_table_styles, cleaned)
    cleaned = re.sub(r"<td([^>]*)>", add_td_styles, cleaned)

    # Ensure outer wrapper
    if not cleaned.startswith("<div>"):
        cleaned = f"<div>{cleaned}</div>"

    return cleaned.strip()


# ======================
# DIAGRAM → SVG EMBED
# ======================
def diagram_image_to_description(diagram_image_xml: str, svg_width_pct: str = "70%") -> str:
    """Convert diagram_image XML into inline SVG <img> HTML."""
    if not diagram_image_xml:
        return ""
    try:
        root = ET.fromstring(diagram_image_xml)
    except ET.ParseError:
        return ""

    # width/height defaults
    width, height = "400", "300"
    for el in root.iter():
        tag = el.tag.split("}")[-1].lower()
        if tag == "width" and "size" in el.attrib:
            width = el.attrib["size"]
        if tag == "height" and "size" in el.attrib:
            height = el.attrib["size"]

    def localname(t): return t.split("}")[-1].lower()
    shapes, trans_stack = [], [(0.0, 0.0)]

    for parent in root.iter():
        for c in list(parent):
            name = localname(c.tag)
            if name == "translate":
                dx, dy = float(c.attrib.get("dx", 0)), float(c.attrib.get("dy", 0))
                px, py = trans_stack[-1]
                trans_stack.append((px + dx, py + dy))
            elif name == "save":
                trans_stack.append(trans_stack[-1])
            elif name == "restore" and len(trans_stack) > 1:
                trans_stack.pop()
            elif name == "rect":
                px, py = trans_stack[-1]
                x, y = float(c.attrib.get("x", 0)) + px, float(c.attrib.get("y", 0)) + py
                w, h = float(c.attrib.get("w", 0)), float(c.attrib.get("h", 0))
                shapes.append(("rect", x, y, w, h))
            elif name == "ellipse":
                px, py = trans_stack[-1]
                x, y = float(c.attrib.get("x", 0)) + px, float(c.attrib.get("y", 0)) + py
                w, h = float(c.attrib.get("w", 0)), float(c.attrib.get("h", 0))
                shapes.append(("ellipse", x + w/2, y + h/2, w/2, h/2))
            elif name == "begin":
                px, py = trans_stack[-1]
                pts = []
                for node in parent:
                    n = localname(node.tag)
                    if n in ("move", "line"):
                        pts.append((float(node.attrib.get("x", 0)) + px, float(node.attrib.get("y", 0)) + py))
                    elif n == "close":
                        break
                if pts:
                    shapes.append(("polygon", pts))

    if not shapes:
        return ""

    # Build SVG
    svg_parts = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}'>"]
    stroke = "#58585b"
    for s in shapes:
        if s[0] == "rect":
            _, x, y, w, h = s
            svg_parts.append(f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='#FFFFFF' stroke='{stroke}' stroke-width='2'/>")
        elif s[0] == "ellipse":
            _, cx, cy, rx, ry = s
            svg_parts.append(f"<ellipse cx='{cx}' cy='{cy}' rx='{rx}' ry='{ry}' fill='#FFFFFF' stroke='{stroke}' stroke-width='2'/>")
        elif s[0] == "polygon":
            pts_str = " ".join([f"{x},{y}" for x, y in s[1]])
            svg_parts.append(f"<polygon points='{pts_str}' fill='#FFFFFF' stroke='{stroke}' stroke-width='2'/>")
    svg_parts.append("</svg>")

    svg_encoded = urllib.parse.quote("".join(svg_parts))
    return f"<div><img alt='diagram' src=\"data:image/svg+xml;utf8,{svg_encoded}\" style='width:{svg_width_pct};' /></div>"
# Input and Output folders
input_folder = r"D:/Polarion/Migration/Transformation/IBM_JSON"
output_folder = r"D:/Polarion/Migration/Transformation/POLARION_JSON"
# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)
# ======================
# KEY MAPPINGS
# ======================
module_mapping = {
    "module_status": "status",
    "created_on": "CreatedOn",
    "modified_on": "ModifiedOn",
    "created_by": "createdBy",
    "modified_by": "ModifiedBy"
}
module_remove_keys = {
    "module_uri",
    "module_id",
    "module_format",
    "linked_artifacts"
}
artifact_mapping = {
    "identifier": "legacyID",
    "artifact_status": "status",
    "created_on": "CreatedOn",
    "modified_on": "ModifiedOn",
    "created_by": "createdBy",
    "modified_by": "ModifiedBy",
    "responsible_group": "responsibleGroup",
    "key_requirement": "keyRequirement",
    "review_status": "reviewStatus",
    "oem_status": "oemStatus",
    "oem-comment": "oemComment",
    "supplier_status": "supplierStatus",
    "supplier-comment": "supplierComment",
    "variant": "variant"
}
# ======================
# VALUE MAPPINGS
# ======================
module_type_mapping = {
    "Admin": "att",
    "Att": "att",
    "Des": "desRS",
    "Dt": "desTS",
    "Req": "sthRS",
    "Rt": "sthTS",
    "Req_Sub": "sysRS",
    "Spec": "sysRS",
    "St": "sysTS"
}
artifact_type_mapping = {
    "Information": "information",
    "Requirements Test": "validationTestCase",
    "Note": "information",
    "Design": "designRequirement",
    "Specification": "systemRequirement",
    "Specification Test": "verificationTestCase",
    "Specification Test Case": "verificationTestCase",
    "Design Test": "verificationTestCase",
    "Stakeholder Requirement": "stakeholderRequirement",
    "Heading": "heading",
    "Image": "information"
}
module_status_mapping = {
    "In work": "draft",
    "In change": "inReview",
    "Rejected": "rejected",
    "Released": "released"
}
artifact_status_mapping = {
    "In work": "draft",
    "In change": "inReview",
    "Approved": "reviewed",
    "Reviewed": "reviewed",
    "Released": "released",
    "Rejected": "rejected"
}
# ✅ New Mapping for space_id
space_id_mapping = {
    "Admin": "_default",
    "Att": "00 ATT",
    "Des": "03 Design",
    "Dt": "04 Verification",
    "Req": "01 Stakeholder",
    "Rt": "05 Validation",
    "Req_Sub": "02 System",
    "Spec": "02 System",
    "St": "04 Verification"
}
# ✅ Link role mapping
link_role_mapping = {
    "derived": "refine",
    "satisfies": "satisfy",
    "reference": "reference",
    "verifies": "verify"
}

# keyRequirement mapping
key_requirement_mapping = {
    "TOP10": "yes",
    "Value Proposition": "yes",
    "Platform": "no",
    "n/a": "no"
}

reviewStatus_mapping={
    "n/a":"na",
    "Clarify":"clarify",
    "Accepted":"accepted",
    "Rejected":"rejected"
}

oemStatus_mapping={
    "n/a":"na",
    "not to evaluate":"notToevaluate",
    "To Evaluate":"toEvaluate",
    "Not Accepted":"notAccepted",
    "Accepted":"accepted"
}

variant_mapping={
    "Variant 1":"v1",
    "Variant 2":"v2",
    "Variant 3":"v3"
}

supplierStatus_mapping={
    "n/a":"na",
    "to be clarified":"toBeclarified",
    "Agreed":"agreed",
    "Not Agreed":"notAgreed",
    "PartlyAgreed":"partlyAgreed"
}

responsible_group_mapping = {
    "n/a": "na",
    "Simulation": ["development", "afterMarketService"],
    "Approval": [
        "prcApproval",
        "prc",
        "prcChemical",
        "configurationManagement",
        "engineeringCosts",
        "testManagement"
    ],
    "Development": [
        "development",
        "developmentSystem",
        "developmentTool",
        "developmentInserts",
        "developmentDrive",
        "developmentMotor",
        "developmentElectronics",
        "developmentSoftware",
        "developmentElectronicsHardware",
        "developmentElectronicsSoftware",
        "developmentMechanics",
        "developmentMechanicsOptics",
        "developmentMechantronicsSensing",
        "developmentService",
        "marketingEngineering"
    ],
    "Marketing": [
        "marketing",
        "materialsManagement",
        "plantEngineering",
        "projectManagement",
        "qualityManagement",
        "requirementsManagement",
        "riskManagement",
        "systemsEngineering",
        "supplyChain",
        "sustainability",
        "technicalMarketing"
    ],
    "Testing": [
        "testManagement",
        "devPartner",
        "oem"
    ]

}

# ======================
# TRANSFORM FUNCTIONS
# ======================
def transform_linked_artifact(link):
    new_link = {}
    for key, value in link.items():
        if key == "identifier":
            new_link["legacyID"] = value
        elif key == "link_role":
            new_link["link_role"] = link_role_mapping.get(value, value)
        elif key in {"uri", "title", "link_role_uri", "link_role_label", "direction"}:
            continue
        else:
            new_link[key] = value
    return new_link


def transform_artifact(artifact):
    new_artifact = {}
    primary_html, primary_html_local, diagram_image_xml = None, None, None
    orig_description = artifact.get("description", "") or ""

    # copy mapped keys
    for key, value in artifact.items():
        if key in artifact_mapping:
            new_key = artifact_mapping[key]
            new_value = value
            if new_key == "status" and value in artifact_status_mapping:
                new_value = artifact_status_mapping[value]
            if new_key == "keyRequirement" and value in key_requirement_mapping:
                new_value = key_requirement_mapping[value]
            if new_key == "reviewStatus" and value in reviewStatus_mapping:
                new_value = reviewStatus_mapping[value]
            if new_key == "oemStatus" and value in oemStatus_mapping:
                new_value = oemStatus_mapping[value]
            if new_key == "variant" and value in variant_mapping:
                new_value = variant_mapping[value]
            if new_key == "supplierStatus" and value in supplierStatus_mapping:
                new_value = supplierStatus_mapping[value]
            if new_key == "responsibleGroup":
                mapped = responsible_group_mapping.get(value)
                new_value = mapped if isinstance(mapped, list) else ([value] if value else [])
            new_artifact[new_key] = new_value

        elif key == "artifact_type":
            new_artifact[key] = artifact_type_mapping.get(value, value)
        elif key == "primary_text_html":
            primary_html = value
        elif key == "primary_text_html_local":
            primary_html_local = value
        elif key == "description":
            pass  # merged later
        elif key == "diagram_image":
            diagram_image_xml = value
        else:
            new_artifact[key] = value

    # Build description
    desc_parts = []
    if diagram_image_xml:
        html = diagram_image_to_description(diagram_image_xml, svg_width_pct="70%")
        if html:
            desc_parts.append(html)
    if primary_html:
        cleaned = clean_primary_html(primary_html)
        if cleaned and cleaned.strip() != "<div></div>":
            desc_parts.append(cleaned)
    if primary_html_local:
        cleaned_local = clean_primary_html(primary_html_local)
        if cleaned_local and cleaned_local.strip() != "<div></div>":
            desc_parts.append(cleaned_local)
    if orig_description.strip():
        desc_parts.append("Description:<hr width='100%' size='2'>" + orig_description)

    # Deduplicate parts
    seen, unique_parts = set(), []
    for part in desc_parts:
        if part not in seen:
            unique_parts.append(part)
            seen.add(part)
    if unique_parts:
        new_artifact["description"] = "".join(unique_parts)

    # Linked artifacts
    if "linked_artifacts" in new_artifact and isinstance(new_artifact["linked_artifacts"], list):
        new_artifact["linked_artifacts"] = [transform_linked_artifact(l) for l in new_artifact["linked_artifacts"]]

    # Children
    if "children" in new_artifact and isinstance(new_artifact["children"], list):
        new_artifact["children"] = [transform_artifact(c) for c in new_artifact["children"]]

    # Attachments
    attachments = []
    if artifact.get("wrapped_resource_saved_as"):
        rel = artifact["wrapped_resource_saved_as"].split("modules_Test_Project_Template\\")[-1]
        name = os.path.splitext(os.path.basename(rel))[0]
        attachments.append({"file_path": rel, "file_name_in_polarion": name, "title": name})
    if artifact.get("embedded_wrapped_resources_saved"):
        for full_path in artifact["embedded_wrapped_resources_saved"]:
            rel = full_path.split("modules_Test_Project_Template\\")[-1]
            name = os.path.splitext(os.path.basename(rel))[0]
            attachments.append({"file_path": rel, "file_name_in_polarion": name, "title": name})
    if attachments:
        new_artifact.setdefault("attachments", []).extend(attachments)

    return new_artifact

def transform_json(data):
    new_data = {}
    for key, value in data.items():
        if key in module_remove_keys:
            continue
        elif key in {"structure", "artifact_uris_in_module_order"}:
            continue  # skip completely
        elif key in module_mapping:
            new_key = module_mapping[key]
            new_value = value
            if new_key == "status" and value in module_status_mapping:
                new_value = module_status_mapping[value]
            new_data[new_key] = new_value
        elif key == "module_type":
            mapped_type = module_type_mapping.get(value, value)
            new_data[key] = mapped_type
            # ✅ Add space_id
            new_data["space_id"] = space_id_mapping.get(value, "_default")
        elif key == "module_title":
            new_data[key] = value
        elif key == "artifacts" and isinstance(value, list):
            new_data["artifacts"] = [transform_artifact(a) for a in value]
        else:
            new_data[key] = value
    return new_data

def count_artifacts(artifacts):
    count = 0
    for artifact in artifacts:
        count += 1
        if "children" in artifact and isinstance(artifact["children"], list):
            count += count_artifacts(artifact["children"])
    return count
# ======================
# MAIN PROCESS
# ======================
total_files = 0
total_artifacts = 0
total_time = 0
for filename in os.listdir(input_folder):
    if filename.endswith(".json"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        start_time = time.time()
        try:
            with open(input_path, "r", encoding="utf-8") as infile:
                data = json.load(infile)
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
            continue
        transformed = transform_json(data)
        try:
            with open(output_path, "w", encoding="utf-8") as outfile:
                json.dump(transformed, outfile, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error writing {filename}: {e}")
            continue
        artifacts_count = count_artifacts(transformed.get("artifacts", []))
        elapsed_time = round(time.time() - start_time, 2)
        total_files += 1
        total_artifacts += artifacts_count
        total_time += elapsed_time
        module_title = transformed.get("module_title", "Unknown Title")
        print(f"✅ Processed: {module_title}   | Work items: {artifacts_count}   | Time: {elapsed_time} sec")

# ✅ Final summary
# print(f"\n Summary: {total_files} files | {total_artifacts} artifacts | {total_time} sec total")
                           
