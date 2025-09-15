
import os
import json
import time
import re
# ======================
# CLEANER FUNCTION
# ======================
def clean_primary_html(html_text: str) -> str:
    if not html_text:
        return ""

    cleaned = html_text

    # 1. Remove <ns0:primarytext ...> wrapper
    cleaned = re.sub(r"</?ns0:primarytext[^>]*>", "", cleaned)

    # 2. Replace "html:" prefixes correctly (opening vs closing)
    cleaned = re.sub(r"<html:([a-zA-Z0-9]+)", r"<\1", cleaned)     # <html:sub> → <sub>
    cleaned = re.sub(r"</html:([a-zA-Z0-9]+)>", r"</\1>", cleaned) # </html:sub> → </sub>

    # 3. Remove dir and id attributes
    cleaned = re.sub(r'\s*dir="[^"]*"', '', cleaned)
    cleaned = re.sub(r'\s*id="[^"]*"', '', cleaned)

    # 4. Remove <img> tags (if any)
    cleaned = re.sub(r"<img[^>]*>", "", cleaned)

    # 5. Normalize spaces & remove newlines
    cleaned = re.sub(r"\n+", " ", cleaned)       # replace newlines with space
    cleaned = re.sub(r"\s{2,}", " ", cleaned)   # collapse multiple spaces

    # 6. Remove empty <p> or <div>
    cleaned = re.sub(r"<p>\s*(?:&nbsp;)?\s*</p>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<div>\s*(?:&nbsp;)?\s*</div>", "", cleaned, flags=re.IGNORECASE)

    # 7. Ensure proper closing tags (replace self-nesting issues)
    cleaned = re.sub(r"(</p>\s*<p>\s*)+", "</p><p>", cleaned)
    cleaned = re.sub(r"(</div>\s*<div>\s*)+", "</div><div>", cleaned)

    # 8. Fix duplicated inline tags (<sub><sub>, etc.)
    cleaned = re.sub(r"<(i|u|b|sub|sup)><\1>", r"<\1>", cleaned)
    cleaned = re.sub(r"</(i|u|b|sub|sup)></\1>", r"</\1>", cleaned)

    # 9. Ensure outer <div><p> ... </p></div> wrapping
    if not cleaned.startswith("<div>"):
        cleaned = f"<div>{cleaned}</div>"
    if not re.search(r"</p>\s*</div>$", cleaned):
        cleaned = re.sub(r"(</p>)\s*</div>$", r"\1</div>", cleaned)

    return cleaned.strip()


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
    "supplier-comment": "supplierComment"
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
            continue  # remove unwanted keys
        else:
            new_link[key] = value
    return new_link

def transform_artifact(artifact):
    new_artifact = {}
    original_description = artifact.get("description", "")
    for key, value in artifact.items():
        if key in artifact_mapping:
            new_key = artifact_mapping[key]
            new_value = value
            if new_key == "status" and value in artifact_status_mapping:
                new_value = artifact_status_mapping[value]
            new_artifact[new_key] = new_value
        elif key == "artifact_type":
            new_artifact[key] = artifact_type_mapping.get(value, value)
        elif key == "primary_text_html":
            valid_html = clean_primary_html(value)
            merged_description = valid_html
            if original_description.strip():
                merged_description += "<br/><br/>Description:<br/>-----------------------------------<br/>" + original_description
            new_artifact["description"] = merged_description
        elif key == "primary_text_html_local":
            new_artifact[key] = clean_primary_html(value)
        elif key == "description":
            continue
        else:
            new_artifact[key] = value
    # ✅ Handle linked artifacts
    if "linked_artifacts" in new_artifact and isinstance(new_artifact["linked_artifacts"], list):
        new_artifact["linked_artifacts"] = [
            transform_linked_artifact(link) for link in new_artifact["linked_artifacts"]
        ]
    # ✅ Handle children recursively
    if "children" in new_artifact and isinstance(new_artifact["children"], list):
        new_artifact["children"] = [transform_artifact(child) for child in new_artifact["children"]]
    # ✅ Collect attachments
    attachments = []
    # Handle wrapped_resource_saved_as (single file)
    if artifact.get("wrapped_resource_saved_as"):
        full_path = artifact["wrapped_resource_saved_as"]
        relative_path = full_path.split("modules_Test_Project_Template\\")[-1]
        file_name = os.path.splitext(os.path.basename(relative_path))[0]
        attachments.append({
            "file_path": relative_path,
            "file_name_in_polarion": file_name,
            "title": file_name
        })
    # Handle embedded_wrapped_resources_saved (list of files)
    if artifact.get("embedded_wrapped_resources_saved"):
        for full_path in artifact["embedded_wrapped_resources_saved"]:
            relative_path = full_path.split("modules_Test_Project_Template\\")[-1]
            file_name = os.path.splitext(os.path.basename(relative_path))[0]
            attachments.append({
                "file_path": relative_path,
                "file_name_in_polarion": file_name,
                "title": file_name
            })
    # Merge into existing attachments list if present
    if attachments:
        if "attachments" not in new_artifact:
            new_artifact["attachments"] = []
        new_artifact["attachments"].extend(attachments)
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
                           