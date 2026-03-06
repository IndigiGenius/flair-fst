/**
 * FLAIR-FST Web Component implementation
 */

import debounce from "debounce";
import { FST, FSTSchema } from "./jsfoma.zod.js";
import {
    Bibliography,
    BibliographySchema,
    Glossary,
    Gloss,
    GlossarySchema,
} from "./api.zod.js";
import {
    add_final_star,
    apply,
    compose,
    generate,
    linearFST,
    project,
} from "./jsfoma.js";
// @ts-ignore
import generatedIcon from "./generated-icon.png";

class FlairFST extends HTMLElement {
    morphology: FST | null = null;
    orthography: FST | null = null;
    bibliography: Bibliography | null = null;
    glossary: Glossary | null = null;

    wordBox: HTMLInputElement;
    morphBox: HTMLElement;
    wordForms: HTMLElement;
    searchForm: HTMLFormElement;
    currentItem: HTMLElement | null = null;

    constructor() {
        super();
        const shadow = this.attachShadow({ mode: "open"});
        shadow.innerHTML = `
<style type="text/css">
:host {
    display: flex;
    flex-direction: row;
    box-sizing: border-box;
    gap: 1%;
}
*,
*::before,
*::after {
    box-sizing: inherit;
}
.search {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    padding: 0px;
    background: #ffffff;
    flex: 2;
    max-width: 40%;
    box-sizing: border-box;
}
#searchform {
    position: relative;
    width: 100%;
}
#wordbox {
    min-width: 75%;
    border-radius: 0;
    width: 100%;
    padding: 10px 14px;
    font-size: 16px;
    background-color: #f2f2f2;
    border: 1px solid #ccc;
    border-radius: 8px;
    outline: none;
    margin-bottom: 20px;
}
#wordforms {
    list-style: none;
    padding: 0;
    margin: 0;
    width: 100%;
    position: absolute;
    background: white;
    overflow-y: auto;
    /* We can't contain it in the column because responsive */
    max-height: 70vh;
    font-weight: 400;
    font-size: 14px;
    line-height: 20px;
    letter-spacing: 0%;
}
#wordforms li {
    display: block;
    width: 100%;
    padding: 4px;
    border: none;
}
#wordforms li.selected {
    background: #e9f3fb;
    color: #1c5b97;
    font-weight: 600;
}
#morphbox  {
    margin-bottom: 1em;
    flex: 3;
    flex-direction: column;
    max-width: 80%;
    width: 5px;
}
#morphbox article {
    margin-bottom: 1em;
}
.igt {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 16px;
    gap: 24px;
    background: #ffffff;
    /* Grays/200 */
    border: 1px solid #e9eaeb;
    border-radius: 8px;
    /* Inside auto layout */
    flex: 3;
    max-width: 100%;
    order: 0;
    align-self: stretch;
    flex-grow: 0;
}
.igtrow {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    flex: 1;
}
.igtrow div {
    flex: 1;
}
.morphs-and-glosses-container {
    /* The container that has all the morphs and glosses for a search result */
    display: flex;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 16px;
    width: 100%;
}

.morphs-and-glosses-container > * {
    /* Handle CSS for all children of the container */
    box-sizing: border-box; /* Include padding and borders in size */
    flex-shrink: 1; /* Allow shrinking to fit */
    max-width: 100%; /* Prevent children from exceeding container width */
}

.morph-and-gloss-row {
    display: flex;
    flex-direction: row;

    align-items: center;
    padding: 0px;
    gap: 12px;

    /* Inside auto layout */
    flex: none;
    order: 1;
    flex-grow: 0;
}

.morph-column {
    display: flex;
    flex-direction: column;
}

.gloss-column {
    display: flex;
    flex-direction: column;
}

.morph {
    /* Morph styling */

    /* Text md/Medium */
    font-style: normal;
    font-weight: 550;
    font-size: 16px;
    line-height: 24px;
    /* identical to box height, or 150% */

    color: #000000;
    flex: 1;
}

.gloss {
    /* Gloss styling */

    /* Text sm/Regular */
    font-style: normal;
    font-weight: 400;
    font-size: 14px;
    line-height: 20px;

    color: #000000;
    flex: 1;
}

.form-row {
    display: flex;
    flex-direction: row;
    align-items: flex-start;
    padding: 0px;
    gap: 8px;
}

.form-row-word {
    margin: 0;
    text-align: left;
    font-style: normal;
    font-weight: 600;
    font-size: 24px;
    line-height: 32px;
    color: #000000;
}
hr.form-row-divider {
    height: 1px;
    background: #d9d9d9;
}
.validation-icon {
    display: block;
    margin: 0 auto;
    width: 32px;
    height: 34px;
    flex: none;
    order: 1;
    flex-grow: 0;
}
.tooltip {
    background: #0a2a42;
    color: white;
    display: none;
    position: absolute;
    top: 0;
    left: auto;
    right: 40px;
    max-width: 270px;
    white-space: nowrap;
    height: auto;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 14px;
    z-index: 10;
    box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
}
.triangle {
    position: absolute;
    top: 50%;
    right: -10px;
    transform: translateY(-50%);
    width: 0;
    height: 0;
    border-style: solid;
    border-width: 6px 0 6px 10px;
    border-color: transparent transparent transparent #0a2a42;
}
a.ref {
    text-decoration: none;
    color: #1c5b97;
}
</style>
<div class="search">
  <form id="searchform">
    <input
      type="search"
      role="combobox"
      placeholder="Enter a word..."
      id="wordbox"
      autocomplete="off"
      />
    <ul role="listbox" id="wordforms"></ul>
  </form>
</div>
<div id="morphbox"></div>
`;
        this.wordBox = shadow.getElementById("wordbox") as HTMLInputElement;
        this.morphBox = shadow.getElementById("morphbox") as HTMLElement;
        this.searchForm = shadow.getElementById(
            "searchform",
        ) as HTMLFormElement;
        this.wordForms = shadow.getElementById("wordforms") as HTMLElement;
    }

    async connectedCallback(this: FlairFST) {
        const baseURI = this.getAttribute("base");
        if (baseURI) {
            await this.loadFromURI(baseURI);
        } else {
            this.loadFromHTML();
        }
        this.initUI();
    }

    /**
     * Load FST data from JSON files under a base URL.
     */
    async loadFromURI(this: FlairFST, baseURI: string) {
        let response = await fetch(`${baseURI}/orthography.json`);
        if (response.ok) {
            this.orthography = FSTSchema.parse(await response.json());
        }
        response = await fetch(`${baseURI}/morphology.json`);
        if (response.ok) {
            this.morphology = FSTSchema.parse(await response.json());
        }
        response = await fetch(`${baseURI}/bibliography.json`);
        if (response.ok) {
            this.bibliography = BibliographySchema.parse(await response.json());
        }
        response = await fetch(`${baseURI}/glossary.json`);
        if (response.ok) {
            this.glossary = GlossarySchema.parse(await response.json());
        }
    }

    /**
     * Load FST data from HTML <script> and <dl> elements.
     */
    loadFromHTML(this: FlairFST) {
        const orthoscript = this.querySelector("script.orthography");
        if (orthoscript && orthoscript.textContent)
            this.orthography = FSTSchema.parse(JSON.parse(orthoscript.textContent));
        const morphoscript = this.querySelector("script.morphology");
        if (morphoscript && morphoscript.textContent)
            this.morphology = FSTSchema.parse(JSON.parse(morphoscript.textContent));
        const biblist = this.querySelector("dl.bibliography")
        if (biblist)
            this.bibliography = biblioFromHTML(biblist);
        const glist = this.querySelector("dl.glossary")
        if (glist)
            this.glossary = glossaryFromHTML(glist);
    }

    /**
     * Initialize the user interface.
     */
    initUI(this: FlairFST) {
        this.wordBox.addEventListener(
            "input",
            debounce(() => this.searchInput(), 200),
        );
        this.wordBox.addEventListener("focus", () => this.searchInput());
        this.wordBox.addEventListener("keydown", (e) => this.handleInputKey(e));
        this.searchForm.addEventListener("submit", (e) => this.handleSubmit(e));
    }

    /**
     * React to new input.
     */
    searchInput(this: FlairFST) {
        const text = this.wordBox.value.trim().normalize("NFC");
        if (text.length < 2) {
            this.wordForms.replaceChildren();
            this.currentItem = null;
            return;
        }
        // No FST, then do nothing! (TODO: split
        // morphology/orthography so we can do something if there is
        // no orthography transducer)
        if (this.morphology === null || this.orthography === null) return;
        const approxForm = project(
            compose(linearFST(text, this.morphology.s), this.orthography),
            "down",
        );
        add_final_star(approxForm, 1);
        const approxMatch = compose(this.morphology, approxForm);
        const forms = [];
        const seen = new Set();
        let i = 0;
        for (const [_, form] of generate(approxMatch)) {
            if (seen.has(form)) continue;
            seen.add(form);
            if (i++ == 50) break;
            const li = document.createElement("li");
            li.setAttribute("role", "option");
            li.innerText = form;
            li.addEventListener("mouseenter", () => {
                if (this.currentItem !== null)
                    this.currentItem.classList.remove("selected");
                this.currentItem = li;
                li.classList.add("selected");
            });
            li.addEventListener("mouseleave", () =>
                li.classList.remove("selected"),
            );
            li.addEventListener("click", () => {
                this.wordBox.value = form;
                this.makeIGT();
                // TODO: have introduction text and remove it here
            });
            li.addEventListener("dblclick", () => {
                this.wordBox.value = form;
                this.searchForm.dispatchEvent(new Event("submit"));
            });
            forms.push(li);
        }
        this.wordForms.replaceChildren(...forms);
        this.currentItem = null;
    }

    handleInputKey(this: FlairFST, evt: KeyboardEvent) {
        let nextItem = null;
        switch (evt.key) {
            // Do not allow this, it breaks the FST and cannot be escaped for Reasons
            case ".":
                evt.preventDefault();
                break;
            case "ArrowDown":
            case "Down":
                if (this.currentItem === null) {
                    nextItem = this.wordForms.firstElementChild as HTMLElement;
                } else {
                    nextItem = this.currentItem.nextElementSibling as HTMLElement;
                }
                if (nextItem !== null) {
                    if (this.currentItem !== null)
                        this.currentItem.classList.remove("selected");
                    this.currentItem = nextItem;
                    this.currentItem.classList.add("selected");
                    if (
                        this.currentItem.offsetTop + this.currentItem.offsetHeight >
                        this.currentItem.parentElement!.scrollTop +
                            this.currentItem.parentElement!.offsetHeight
                    )
                        this.currentItem.scrollIntoView(false);
                }
                break;
            case "ArrowUp":
            case "Up":
                if (this.currentItem !== null)
                    nextItem =
                        this.currentItem.previousElementSibling as HTMLElement;
                if (nextItem !== null) {
                    if (this.currentItem !== null)
                        this.currentItem.classList.remove("selected");
                    this.currentItem = nextItem;
                    this.currentItem.classList.add("selected");
                    if (
                        this.currentItem.offsetTop <
                        this.currentItem.parentElement!.scrollTop
                    )
                        this.currentItem.scrollIntoView(true);
                }
                break;
            case "Escape":
            case "Esc":
                // Close the dropdown
                this.wordForms.replaceChildren();
                this.currentItem = null;
                break;
            case "Enter":
                if (evt.key == "Enter" && this.currentItem !== null) {
                    this.wordBox.value = this.currentItem.innerText;
                    this.searchForm.dispatchEvent(new Event("submit"));
                }
                break;
        }
    }

    handleSubmit(this: FlairFST, evt: SubmitEvent) {
        if (this.morphology === null || this.orthography === null) return;

        // Search (approximately) for the thing we entered
        const text = this.wordBox.value.trim().normalize("NFC");

        // FIXME: Should use weights here, but for the moment we will
        // first try to analyze the exact input (that is pretty fast)
        let iter = apply(this.morphology, text, "up").next();
        if (iter.done) {
            const approxForm = project(
                compose(linearFST(text, this.morphology.s), this.orthography),
                "down",
            );
            const approxMatch = compose(this.morphology, approxForm);
            iter = generate(approxMatch).next();
        }
        if (!iter.done) this.wordBox.value = iter.value[1];
        this.makeIGT();
        // Close the dropdown
        this.wordForms.replaceChildren();
        this.currentItem = null;
        // Don't actually submit the form
        evt.preventDefault();
    }

    /**
     * Create an IGT (interlinear glossed text) for a given word that
     * is selected by the user and add it to the UI.
     *
     * TODO: is "word" the term that we should use here?
     */
    makeIGT(this: FlairFST) {
        if (this.morphology === null || this.orthography === null) return;
        const text = this.wordBox.value.trim().normalize("NFC"); // extract the word from the search box
        this.morphBox.replaceChildren(); // remove children nodes from the morphbox element
        for (const [morph, form] of apply(this.morphology, text, "up")) {
            const article = this.makeArticle(morph, form);
            this.morphBox.appendChild(article);
        }
    }

    /**
     * Make an HTML article element that displays the results of the user's search.
     *
     * TODO: polish this TypeDoc
     * @param morph
     * @param form the written text of the searched word, including diacritics (TODO: verify this, and is there a better name?)
     * @returns
     */
    makeArticle(this: FlairFST, morph: string, form: string) {
        // It may be useful to get an alignment here but that is somewhat
        // more difficult to do with the current FST setup.
        const { morphs, glosses } = this.getMorphsAndGlosses(morph);

        const interlinearGlossedText = document.createElement("div"); // interlinear glossed text element
        interlinearGlossedText.setAttribute("class", "igt");

        // Determine if this is an attested form (this is a bit more
        // complicated than just looking it up in the glossDict)
        const ref = this.getReference(form, morphs);

        // Form Row
        const formRow = this.createFormRow(form, ref);
        interlinearGlossedText.appendChild(formRow);

        // Morphs and Glosses
        const morphAndGlossColumns = this.createMorphAndGlossColumns(
            morphs,
            glosses,
        );
        interlinearGlossedText.appendChild(morphAndGlossColumns);

        // Wrap in an article element
        const article = document.createElement("article");
        article.setAttribute("class", "wordSearchResult");
        article.appendChild(interlinearGlossedText);
        return article;
    }

    /**
     * Get the morphs and glosses lists for a given morph input
     *
     * TODO: is it bad naming that we have an input morph from which we extract a `morphs` list? feels wrong.
     * @param morph
     * @returns
     */
    getMorphsAndGlosses(
        this: FlairFST,
        morph: string,
    ): {
        morphs: Array<string>;
        glosses: Array<Gloss>;
    } {
        // It may be useful to get an alignment here but that is somewhat
        // more difficult to do with the current FST setup.
        const morphs: Array<string> = [];
        const glosses: Array<Gloss> = [];
        // FIXME: This simply does not work for prefixes
        const morphrx = /([=+-][^=+-]+)/g;

        if (this.glossary === null) return { morphs: morphs, glosses: glosses };
        const morphRegexMatches = [...morph.matchAll(morphrx)];
        // let morphRegexMatch = morphrx.exec(morph);
        if (morphRegexMatches.length > 0) {
            // Extract the root, add it to `morphs` and add its gloss if one exists
            const root = morph.substring(0, morphRegexMatches[0].index);
            morphs.push(root);
            // TODO: handle i18n here and below
            glosses.push(this.glossary[root]?._default ?? root);

            // Process the regex matches in the morph
            for (const match of morphRegexMatches) {
                const ending = match[0];
                morphs.push(ending);
                glosses.push(this.glossary[ending]?._default ?? ending);
            }
        } else {
            // Handle the case with no regex matches
            morphs.push(morph);
            glosses.push(this.glossary[morph]?._default ?? morph);
        }
        return { morphs: morphs, glosses: glosses };
    }

    /**
     * Create the row element for the Form of the searched word
     * @param form The form being displayed
     * @returns row: the form row element, attest: true if the form has a reference to include
     */
    createFormRow(
        this: FlairFST,
        form: string,
        ref: Gloss | null,
    ): HTMLDivElement {
        const formRow = createDivElement("igtrow");
        formRow.classList.add("form-row");
        const formEl = createDivElement("form-row-word");
        formRow.appendChild(formEl);

        if (ref !== null) {
            formEl.append(form);
            formEl.append(" (attested in\u00a0");
            formEl.append(this.makeRef(ref));
            formEl.append(")");
        } else {
            formEl.append(form);

            const validationIconImage = document.createElement("img");
            validationIconImage.src = generatedIcon;
            validationIconImage.alt = "Experimentally Generated";
            validationIconImage.classList.add("validation-icon");

            const tooltip = createDivElement("tooltip");
            tooltip.textContent = "Experimentally generated";

            // Create the triangle element
            const triangle = createDivElement("triangle");

            // Add hover event listeners to show/hide the tooltip
            validationIconImage.addEventListener("mouseenter", () => {
                tooltip.style.display = "block";
            });
            validationIconImage.addEventListener("mouseleave", () => {
                tooltip.style.display = "none";
            });

            // Wrap the icon and tooltip in a container
            const iconContainer = document.createElement("div");
            // Ensure tooltip is positioned relative to this container
            iconContainer.style.position = "relative";
            iconContainer.appendChild(validationIconImage);

            // Append the triangle to the tooltip
            tooltip.appendChild(triangle);
            iconContainer.appendChild(tooltip);
            formRow.appendChild(iconContainer);
        }
        return formRow;
    }

    /**
     * Determine if a form is attested based on its morphological
     * analysis, returning the attestation if it exists.
     *
     * A form is attested if:
     * - It is present in the glossDict, or
     * - It has a single morph which is present in the glossDict
     *
     * This is because alternation rules apply so we need to use the
     * underlying form ("morph") to determine this.
     *
     * @returns the Gloss with the attestation, or null if non-attested.
     */
    getReference(
        this: FlairFST,
        form: string,
        morphs: Array<string>,
    ): Gloss | null {
        if (this.glossary === null) return null;
        if (form in this.glossary) return this.glossary[form]._default ?? null;
        if (morphs.length == 1 && morphs[0] in this.glossary)
            return this.glossary[morphs[0]]._default ?? null;
        return null;
    }

    /**
     * Make a reference element with possible link.
     */
    makeRef(this: FlairFST, gloss: Gloss): Node {
        if (!gloss.ref || this.bibliography === null || !(gloss.ref in this.bibliography))
            return document.createTextNode("");
        const source = this.bibliography[gloss.ref];
        let url = source.url;
        let linkText = gloss.ref;
        if (url && gloss.page) {
            // It is a string because it could be '29a' or 'iv' (pronounced "eev")
            const page = parseInt(gloss.page);
            const pageOffset = source.pageOffset ?? 0;
            // FIXME: Of course this won't work if it's not really a number
            url += `#page=${page + pageOffset}`;
            linkText += `, page ${page}`;
        }
        if (url) {
            const link = document.createElement("a");
            link.setAttribute("class", "ref");
            link.setAttribute("href", url);
            link.setAttribute("target", "_blank");
            link.append(linkText);
            return link;
        } else {
            return document.createTextNode(linkText);
        }
    }

    createMorphAndGlossColumns(
        this: FlairFST,
        morphs: string[],
        glosses: Gloss[],
    ): HTMLDivElement {
        const morphsAndGlossesContainer = createDivElement(
            "morphs-and-glosses-container",
        );

        const length = Math.min(morphs.length, glosses.length);
        for (let i = 0; i < length; i++) {
            const morphAndGlossRow = this.createMorphAndGlossRow(
                morphs[i],
                glosses[i],
            );
            morphsAndGlossesContainer.appendChild(morphAndGlossRow);
        }

        return morphsAndGlossesContainer;
    }

    /**
     * Create a row element containing a morph and its corresponding gloss.
     * @param morph the morph text
     * @param gloss the gloss object
     * @returns the row element containing the morph and gloss
     */
    createMorphAndGlossRow(
        this: FlairFST,
        morph: string,
        gloss: Gloss,
    ): HTMLDivElement {
        const row = createDivElement("morph-and-gloss-row");

        // Create the morph element
        const morphElement = document.createElement("div");
        morphElement.setAttribute("class", "morph");
        morphElement.innerText = morph;

        // Create the gloss element
        const glossElement = document.createElement("div");
        glossElement.setAttribute("class", "gloss");
        glossElement.append(gloss.gloss);
        if (gloss.ref) {
            glossElement.append("\u00a0(");
            glossElement.append(this.makeRef(gloss));
            glossElement.append(")");
        }

        // Append morph and gloss to the row
        row.appendChild(morphElement);
        row.appendChild(glossElement);

        return row;
    }
}
customElements.define("flair-fst", FlairFST);

/**
 * Create a generic div element
 * @param className class name for the element
 * @returns the element
 */
function createDivElement(className: string): HTMLDivElement {
    const element = document.createElement("div");
    element.setAttribute("class", className);
    return element;
}


/**
 * Create Bibliography from DOM elements.
 */
function biblioFromHTML(biblist: Element): Bibliography {
    const bibliography: Bibliography = {};
    let key: string | null = null;
    for (const el of biblist.children) {
        switch (el.tagName) {
        case "DT":
            key = el.textContent?.trim() || null;
            break;
        case "DD":
            if (key === null) {
                console.log(`Missing key for bibliography entry: ${el}`);
                continue;
            }
            const pageOffset = parseInt(el.getAttribute("data-page-offset") || "0");
            const citation = el.textContent?.trim() || "";
            const link = el.querySelector("a");
            const url = link ? link.getAttribute("href") : null;
            if (url)
                bibliography[key] = {pageOffset, citation, url}
            else
                bibliography[key] = {pageOffset, citation}
            break;
        }
    }
    return bibliography;
}

/**
 * Create Glossary from DOM elements.
 */
function glossaryFromHTML(glist: Element): Glossary {
    const glossary: Glossary = {};
    let key: string | null = null;
    for (const el of glist.children) {
        switch (el.tagName) {
        case "DT":
            key = el.textContent?.trim() || null;
            if (key)
                glossary[key] = {};
            break;
        case "DD":
            if (key === null) {
                console.log(`Missing key for glossary entry: ${el}`);
                continue;
            }
            const lang = el.getAttribute("lang") || "_default";
            const gloss = el.textContent?.trim() || "";
            glossary[key][lang] = {gloss};
            const ref = el.getAttribute("data-ref");
            if (ref)
                glossary[key][lang].ref = ref;
            const form = el.getAttribute("data-form");
            if (form)
                glossary[key][lang].form = form;
            const page = el.getAttribute("data-page");
            if (page)
                glossary[key][lang].page = page;
        }
    }
    return glossary;
}
