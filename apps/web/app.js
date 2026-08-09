const API_URL = "http://127.0.0.1:8000";

const state = {
    searchPage: 1,
    searchLimit: 20,
    searchQuery: "",
    documentsPage: 1,
    documentsLimit: 20,
};

const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const searchStatus = document.getElementById("search-status");
const results = document.getElementById("results");
const searchPagination = document.getElementById("search-pagination");

const documentsStatus = document.getElementById("documents-status");
const documentsList = document.getElementById("documents-list");
const documentsPagination =
    document.getElementById("documents-pagination");

const refreshDocuments =
    document.getElementById("refresh-documents");

const documentForm =
    document.getElementById("document-form");

const documentId =
    document.getElementById("document-id");

const documentTitle =
    document.getElementById("document-title");

const documentUrl =
    document.getElementById("document-url");

const documentDescription =
    document.getElementById("document-description");

const documentContent =
    document.getElementById("document-content");

const formTitle =
    document.getElementById("form-title");

const formStatus =
    document.getElementById("form-status");

const cancelEdit =
    document.getElementById("cancel-edit");

document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        switchView(tab.dataset.view);
    });
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = input.value.trim();

    if (!query) {
        return;
    }

    state.searchQuery = query;
    state.searchPage = 1;

    await search();
});

refreshDocuments.addEventListener("click", async () => {
    await loadDocuments();
});

documentForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    await saveDocument();
});

cancelEdit.addEventListener("click", () => {
    resetDocumentForm();
});

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {}),
        },
    });

    if (!response.ok) {
        let detail = `Request failed: HTTP ${response.status}`;

        try {
            const body = await response.json();

            if (body.detail) {
                detail =
                    typeof body.detail === "string"
                        ? body.detail
                        : JSON.stringify(body.detail);
            }
        } catch {
            // Keep the HTTP error message.
        }

        throw new Error(detail);
    }

    if (response.status === 204) {
        return null;
    }

    return response.json();
}

async function search() {
    const query = state.searchQuery;

    if (!query) {
        return;
    }

    searchStatus.textContent = "Searching...";
    searchStatus.className = "status";
    results.innerHTML = "";
    searchPagination.innerHTML = "";

    try {
        const params = new URLSearchParams({
            q: query,
            page: String(state.searchPage),
            limit: String(state.searchLimit),
        });

        const data = await apiRequest(`/search?${params}`);

        renderSearchResults(data);
        renderPagination(
            searchPagination,
            data.page,
            data.limit,
            data.total,
            (page) => {
                state.searchPage = page;
                search();
            },
        );
    } catch (error) {
        searchStatus.textContent = error.message;
        searchStatus.className = "status error";
    }
}

function renderSearchResults(data) {
    searchStatus.textContent =
        `${data.total} result${data.total === 1 ? "" : "s"} found`;

    if (data.results.length === 0) {
        results.innerHTML = `
            <div class="empty">
                No documents matched your search.
            </div>
        `;
        return;
    }

    results.innerHTML = data.results
        .map((result) => {
            const highlights = Object.values(
                result.highlight || {},
            )
                .flat()
                .map(
                    (value) =>
                        `<div class="highlight">${sanitizeHighlight(value)}</div>`,
                )
                .join("");

            return `
                <article class="result">
                    <h2>
                        <a
                            href="${escapeHtml(result.url)}"
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            ${escapeHtml(result.title)}
                        </a>
                    </h2>

                    <div class="result-url">
                        ${escapeHtml(result.url)}
                    </div>

                    <div class="result-description">
                        ${escapeHtml(result.description)}
                    </div>

                    ${highlights}
                </article>
            `;
        })
        .join("");
}

async function loadDocuments() {
    documentsStatus.textContent = "Loading documents...";
    documentsStatus.className = "status";
    documentsList.innerHTML = "";
    documentsPagination.innerHTML = "";

    try {
        const params = new URLSearchParams({
            page: String(state.documentsPage),
            limit: String(state.documentsLimit),
        });

        const data =
            await apiRequest(`/documents?${params}`);

        renderDocuments(data);

        renderPagination(
            documentsPagination,
            data.page,
            data.limit,
            data.total,
            (page) => {
                state.documentsPage = page;
                loadDocuments();
            },
        );
    } catch (error) {
        documentsStatus.textContent = error.message;
        documentsStatus.className = "status error";
    }
}

function renderDocuments(data) {
    documentsStatus.textContent =
        `${data.total} document${data.total === 1 ? "" : "s"}`;

    if (data.results.length === 0) {
        documentsList.innerHTML = `
            <div class="empty">
                No documents have been indexed yet.
            </div>
        `;
        return;
    }

    documentsList.innerHTML = data.results
        .map((document) => {
            return `
                <article class="document-card">
                    <h3>
                        ${escapeHtml(document.title)}
                    </h3>

                    <div class="document-url">
                        ${escapeHtml(document.url)}
                    </div>

                    <div class="document-description">
                        ${escapeHtml(document.description)}
                    </div>

                    <div class="document-actions">
                        <button
                            data-action="edit"
                            data-id="${escapeHtml(document.id)}"
                        >
                            Edit
                        </button>

                        <button
                            class="secondary"
                            data-action="delete"
                            data-id="${escapeHtml(document.id)}"
                        >
                            Delete
                        </button>
                    </div>
                </article>
            `;
        })
        .join("");

    documentsList
        .querySelectorAll("[data-action='edit']")
        .forEach((button) => {
            button.addEventListener("click", () => {
                editDocument(button.dataset.id);
            });
        });

    documentsList
        .querySelectorAll("[data-action='delete']")
        .forEach((button) => {
            button.addEventListener("click", () => {
                deleteDocument(button.dataset.id);
            });
        });
}

async function editDocument(id) {
    formStatus.textContent = "Loading document...";
    formStatus.className = "status";

    try {
        const document =
            await apiRequest(
                `/documents/${encodeURIComponent(id)}`,
            );

        documentId.value = document.id;
        documentTitle.value = document.title;
        documentUrl.value = document.url;
        documentDescription.value = document.description;
        documentContent.value = document.content;

        formTitle.textContent = "Edit Document";
        cancelEdit.hidden = false;

        formStatus.textContent = "";

        switchView("create-view");
    } catch (error) {
        formStatus.textContent = error.message;
        formStatus.className = "status error";
    }
}

async function saveDocument() {
    formStatus.textContent = "Saving...";
    formStatus.className = "status";

    const payload = {
        title: documentTitle.value.trim(),
        url: documentUrl.value.trim(),
        description: documentDescription.value.trim(),
        content: documentContent.value,
    };

    try {
        const id = documentId.value;

        if (id) {
            await apiRequest(
                `/documents/${encodeURIComponent(id)}`,
                {
                    method: "PUT",
                    body: JSON.stringify(payload),
                },
            );

            formStatus.textContent =
                "Document updated successfully.";
        } else {
            await apiRequest("/documents", {
                method: "POST",
                body: JSON.stringify(payload),
            });

            formStatus.textContent =
                "Document created successfully.";
        }

        resetDocumentForm(false);
        await loadDocuments();
    } catch (error) {
        formStatus.textContent = error.message;
        formStatus.className = "status error";
    }
}

async function deleteDocument(id) {
    const confirmed = window.confirm(
        "Delete this document permanently?",
    );

    if (!confirmed) {
        return;
    }

    documentsStatus.textContent = "Deleting...";
    documentsStatus.className = "status";

    try {
        await apiRequest(
            `/documents/${encodeURIComponent(id)}`,
            {
                method: "DELETE",
            },
        );

        await loadDocuments();
    } catch (error) {
        documentsStatus.textContent = error.message;
        documentsStatus.className = "status error";
    }
}

function resetDocumentForm(clearStatus = true) {
    documentForm.reset();
    documentId.value = "";

    formTitle.textContent = "Add Document";
    cancelEdit.hidden = true;

    if (clearStatus) {
        formStatus.textContent = "";
        formStatus.className = "status";
    }
}

function switchView(viewId) {
    document.querySelectorAll(".view").forEach((view) => {
        view.classList.toggle(
            "active",
            view.id === viewId,
        );
    });

    document.querySelectorAll(".tab").forEach((tab) => {
        tab.classList.toggle(
            "active",
            tab.dataset.view === viewId,
        );
    });

    if (viewId === "documents-view") {
        loadDocuments();
    }
}

function renderPagination(
    container,
    page,
    limit,
    total,
    onPageChange,
) {
    const totalPages =
        Math.max(1, Math.ceil(total / limit));

    if (totalPages <= 1) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = `
        <button
            id="previous-page"
            ${page <= 1 ? "disabled" : ""}
        >
            Previous
        </button>

        <span class="pagination-info">
            Page ${page} of ${totalPages}
        </span>

        <button
            id="next-page"
            ${page >= totalPages ? "disabled" : ""}
        >
            Next
        </button>
    `;

    container
        .querySelector("#previous-page")
        .addEventListener("click", () => {
            onPageChange(page - 1);
        });

    container
        .querySelector("#next-page")
        .addEventListener("click", () => {
            onPageChange(page + 1);
        });
}

function sanitizeHighlight(value) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = value;

    wrapper.querySelectorAll("*").forEach((element) => {
        if (element.tagName.toLowerCase() !== "mark") {
            element.replaceWith(
                document.createTextNode(element.textContent),
            );
        }

        [...element.attributes].forEach((attribute) => {
            element.removeAttribute(attribute.name);
        });
    });

    return wrapper.innerHTML;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}
