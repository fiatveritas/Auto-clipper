/*
 * annotation.js
 *
 * Handles ML dataset annotation.
 *
 * Responsibilities:
 *  - Load annotation schema
 *  - Open annotation dialog
 *  - Load existing labels
 *  - Populate primary event dropdown
 *  - Populate tag checkboxes
 *  - Save annotations
 *  - Save + Next
 */

let annotationSchema = null;
let currentClipId = null;
//let currentJobId = null;

async function initializeAnnotation() {

    try {

        await loadSchema();

        console.log(
            "[Annotation] Schema loaded."
        );

        const dropdown =
            document.getElementById(
                "primaryEvent"
            );

        if (dropdown) {

            dropdown.addEventListener(
                "change",
                updateTags
            );

        }

    }

    catch (error) {

        console.error(error);

    }

}

document.addEventListener(
    "DOMContentLoaded",
    initializeAnnotation
);

async function loadSchema() {

    const response =
        await fetch("/api/schema");

    if (!response.ok) {

        throw new Error(
            "Failed to load annotation schema."
        );

    }

    annotationSchema =
        await response.json();

}

async function openAnnotation(jobId, clipId) {

    currentJobId = jobId;

    currentClipId = clipId;

    if (!annotationSchema) {

    await loadSchema();

}
    populatePrimaryEvents();

    await loadExistingLabel();

    updateTags();

const modal =
    document.getElementById(
        "annotationModal"
    );

if (!modal) {

    console.error(
        "annotationModal not found."
    );

    return;

}

modal.showModal();

}

function populatePrimaryEvents() {

    const dropdown =
        document.getElementById(
            "primaryEvent"
        );

    if (!dropdown)
        return;

    dropdown.innerHTML = "";

    annotationSchema.primary_events.forEach(event => {

        const option =
            document.createElement("option");

        option.value = event;

        option.textContent = event;

        dropdown.appendChild(option);

    });

}

function updateTags() {

    const selected =

        document.getElementById(
            "primaryEvent"
        ).value;

    const container =

        document.getElementById(
            "tagContainer"
        );

    container.innerHTML = "";

    const tags =

        annotationSchema.tag_groups[
            selected
        ] || [];

    tags.forEach(tag => {

        const label =
            document.createElement("label");

        const checkbox =
            document.createElement("input");

        checkbox.type = "checkbox";

        checkbox.value = tag;

        label.appendChild(checkbox);

        label.appendChild(
            document.createTextNode(tag)
        );

        container.appendChild(label);

    });

}

async function loadExistingLabel() {

    const response =

        await fetch(

            `/api/labels/${currentClipId}`

        );

    if (!response.ok)
        return;

    const label =
        await response.json();

    console.log(label);

}

function collectAnnotation() {

    const checkedTags = [];

    document
        .querySelectorAll(
            "#tagContainer input:checked"
        )
        .forEach(input => {

            checkedTags.push(
                input.value
            );

        });

    return {

        is_highlight:

            document
                .getElementById("highlightYes")
                .checked,

        primary_event:

            document
                .getElementById("primaryEvent")
                .value,

        tags:

            checkedTags,

        notes:

            document
                .getElementById("annotationNotes")
                .value

    };

}

async function saveAnnotation() {

    const annotation =
        collectAnnotation();

    const response =
        await fetch(

            `/api/labels/${currentClipId}`,

            {

                method: "POST",

                headers: {

                    "Content-Type":
                        "application/json"

                },

                body: JSON.stringify(
                    annotation
                )

            }

        );

    if (!response.ok) {

const error =
    await response.json();

alert(
    error.error ||
    "Failed to save annotation."
);

        return false;

    }

    console.log(
        "[Annotation] Saved."
    );
    return true;

}

async function saveAndNext() {

    await saveAnnotation();

    console.log(
        "Next clip..."
    );

}

async function onSave() {

    const success = await saveAnnotation();

    if (!success)
        return;

    const modal =
        document.getElementById(
            "annotationModal"
        );

    if (modal) {

        modal.close();

    }

}