const initialElements = [
    { name: "Water", emoji: "💧", time: 0, depth: 0, parents: null },
    { name: "Fire", emoji: "🔥", time: 0, depth: 0, parents: null },
    { name: "Earth", emoji: "🌍", time: 0, depth: 0, parents: null },
    { name: "Wind", emoji: "💨", time: 0, depth: 0, parents: null }
];

let discoveredElements = JSON.parse(localStorage.getItem("infinite-craft-elements")) || initialElements;

// Migration: Ensure all elements have new properties
discoveredElements.forEach(el => {
    if (el.time === undefined) el.time = 0;
    if (el.depth === undefined) el.depth = (initialElements.some(i => i.name === el.name) ? 0 : 1);
    if (el.parents === undefined) el.parents = null;
    if (el.recipes === undefined) {
        el.recipes = el.parents ? [el.parents] : [];
    }
});

let instances = [];
let isDragging = false;
let draggedElement = null;
let dragOffsetX = 0;
let dragOffsetY = 0;

const craftingArea = document.getElementById("crafting-area");
const elementsList = document.getElementById("elements-list");
const searchInput = document.getElementById("search-input");
const sortSelect = document.getElementById("sort-select");
const clearBtn = document.getElementById("clear-btn");
const resetBtn = document.getElementById("reset-btn");

// Modal elements moved to modal.js

function saveProgress() {
    localStorage.setItem("infinite-craft-elements", JSON.stringify(discoveredElements));
}

function getWordCount(name) {
    return name.trim().split(/\s+/).length;
}

function getRecipeCount(el) {
    return (el.recipes && el.recipes.length) || (el.parents ? 1 : 0);
}

// New filter elements
const wordOp = document.getElementById("word-op");
const wordValue = document.getElementById("word-value");
const depthOp = document.getElementById("depth-op");
const depthValue = document.getElementById("depth-value");
const recipeFilter = document.getElementById("recipe-filter");
const statsCount = document.getElementById("stats-count");
const statsBtn = document.getElementById("stats-btn");
const statsModal = document.getElementById("stats-modal");
const statsGrid = document.getElementById("stats-grid");
const closeStats = document.querySelector(".close-stats");

// Enable/disable number inputs based on operator selection
if (wordOp) {
    wordOp.addEventListener("change", () => {
        wordValue.disabled = wordOp.value === "all";
        if (wordOp.value === "all") wordValue.value = "";
        renderSidebar();
    });
}
if (depthOp) {
    depthOp.addEventListener("change", () => {
        depthValue.disabled = depthOp.value === "all";
        if (depthOp.value === "all") depthValue.value = "";
        renderSidebar();
    });
}

function matchesFilter(value, op, target) {
    if (op === "all" || target === "") return true;
    const t = parseInt(target);
    if (isNaN(t)) return true;
    if (op === "=") return value === t;
    if (op === "<=") return value <= t;
    if (op === ">=") return value >= t;
    return true;
}

function updateStatsCount() {
    if (statsCount) {
        statsCount.textContent = `${discoveredElements.length} elements`;
    }
}

function renderSidebar() {
    elementsList.innerHTML = "";
    const filter = searchInput.value.toLowerCase();
    const sortMode = sortSelect.value;
    const wOp = wordOp ? wordOp.value : "all";
    const wVal = wordValue ? wordValue.value : "";
    const dOp = depthOp ? depthOp.value : "all";
    const dVal = depthValue ? depthValue.value : "";
    const recipeFilterValue = recipeFilter ? recipeFilter.value : "all";
    
    const filtered = discoveredElements
        .filter(el => el.name.toLowerCase().includes(filter))
        .filter(el => matchesFilter(getWordCount(el.name), wOp, wVal))
        .filter(el => matchesFilter(el.depth || 0, dOp, dVal))
        .filter(el => {
            if (recipeFilterValue === "all") return true;
            const rc = getRecipeCount(el);
            if (recipeFilterValue === "multi") return rc > 1;
            if (recipeFilterValue === "single") return rc === 1;
            if (recipeFilterValue === "base") return rc === 0;
            return true;
        })
        .sort((a, b) => {
            if (sortMode === "name") {
                return a.name.localeCompare(b.name);
            } else if (sortMode === "time-desc") {
                return b.time - a.time || a.name.localeCompare(b.name);
            } else if (sortMode === "time-asc") {
                return a.time - b.time || a.name.localeCompare(b.name);
            } else if (sortMode === "depth-asc") {
                return a.depth - b.depth || a.name.localeCompare(b.name);
            } else if (sortMode === "depth-desc") {
                return b.depth - a.depth || a.name.localeCompare(b.name);
            } else if (sortMode === "words-asc") {
                return getWordCount(a.name) - getWordCount(b.name) || a.name.localeCompare(b.name);
            } else if (sortMode === "words-desc") {
                return getWordCount(b.name) - getWordCount(a.name) || a.name.localeCompare(b.name);
            }
            return 0;
        });
    
    filtered.forEach(el => {
            const div = document.createElement("div");
            div.className = "element";
            div.innerHTML = `<span class="emoji">${el.emoji}</span> <span class="name">${el.name}</span>`;
            div.draggable = true;
            
            div.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("application/json", JSON.stringify(el));
                e.dataTransfer.effectAllowed = "copy";
            });
            
            div.addEventListener("click", () => showElementDetails(el));
            
            elementsList.appendChild(div);
        });
    
    updateStatsCount();
}

// Modal functions moved to modal.js

function createInstance(element, x, y) {
    const div = document.createElement("div");
    div.className = "element instance";
    div.innerHTML = `<span class="emoji">${element.emoji}</span> <span class="name">${element.name}</span>`;
    div.style.left = x + "px";
    div.style.top = y + "px";
    
    const instance = {
        id: Date.now() + Math.random(),
        element: element,
        dom: div,
        x: x,
        y: y
    };
    
    div.addEventListener("mousedown", (e) => {
        isDragging = true;
        draggedElement = instance;
        const rect = div.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
        div.style.zIndex = 100;
    });

    craftingArea.appendChild(div);
    instances.push(instance);
    return instance;
}

function removeInstance(instance) {
    if (instance.dom && instance.dom.parentNode) {
        instance.dom.parentNode.removeChild(instance.dom);
    }
    instances = instances.filter(i => i !== instance);
}

async function combineElements(instance1, instance2) {
    // Visual feedback
    instance1.dom.classList.add("combining");
    instance2.dom.classList.add("combining");

    const el1 = instance1.element;
    const el2 = instance2.element;

    try {
        const response = await fetch("/api/combine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                element1: el1.name,
                element2: el2.name
            })
        });

        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `API Error: ${response.status}`);
        }

        const data = await response.json();
        
        // Remove old instances
        removeInstance(instance1);
        removeInstance(instance2);

        // Create new instance at center
        const newX = (instance1.x + instance2.x) / 2;
        const newY = (instance1.y + instance2.y) / 2;
        
        const newElement = { 
            name: data.result, 
            emoji: data.emoji,
            time: Date.now(),
            depth: Math.max(el1.depth || 0, el2.depth || 0) + 1,
            parents: [el1.name, el2.name],
            recipes: [[el1.name, el2.name]]
        };
        
        // Check if new discovery
        const existing = discoveredElements.find(e => e.name === newElement.name);
        if (!existing) {
            discoveredElements.push(newElement);
            saveProgress();
            renderSidebar();
        } else {
            // Use existing element data (to keep original discovery time and depth)
            newElement.time = existing.time;
            newElement.depth = existing.depth;
            newElement.parents = existing.parents;
            newElement.recipes = existing.recipes || (existing.parents ? [existing.parents] : []);

            // Check if this is a new recipe for the existing element
            const currentRecipe = [el1.name, el2.name];
            const recipeExists = newElement.recipes.some(r => 
                (r[0] === currentRecipe[0] && r[1] === currentRecipe[1]) ||
                (r[0] === currentRecipe[1] && r[1] === currentRecipe[0])
            );

            if (!recipeExists) {
                newElement.recipes.push(currentRecipe);
                existing.recipes = newElement.recipes; // Update the stored element
                saveProgress();
            }
        }

        const newInstance = createInstance(newElement, newX, newY);
        if (!existing) {
            newInstance.dom.classList.add("new-discovery");
        }

    } catch (error) {
        console.error("Crafting failed:", error);
        alert(`Crafting failed: ${error.message}`);
        instance1.dom.classList.remove("combining");
        instance2.dom.classList.remove("combining");
    }
}

function checkCollisions(targetInstance) {
    const rect1 = targetInstance.dom.getBoundingClientRect();
    
    for (const instance of instances) {
        if (instance === targetInstance) continue;
        
        const rect2 = instance.dom.getBoundingClientRect();
        
        if (!(rect1.right < rect2.left || 
              rect1.left > rect2.right || 
              rect1.bottom < rect2.top || 
              rect1.top > rect2.bottom)) {
            return instance;
        }
    }
    return null;
}

// Event Listeners
craftingArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
});

craftingArea.addEventListener("drop", (e) => {
    e.preventDefault();
    const data = e.dataTransfer.getData("application/json");
    if (data) {
        const element = JSON.parse(data);
        const rect = craftingArea.getBoundingClientRect();
        const x = e.clientX - rect.left - 40; // Center roughly
        const y = e.clientY - rect.top - 20;
        createInstance(element, x, y);
    }
});

document.addEventListener("mousemove", (e) => {
    if (isDragging && draggedElement) {
        const rect = craftingArea.getBoundingClientRect();
        let x = e.clientX - rect.left - dragOffsetX;
        let y = e.clientY - rect.top - dragOffsetY;
        
        draggedElement.x = x;
        draggedElement.y = y;
        draggedElement.dom.style.left = x + "px";
        draggedElement.dom.style.top = y + "px";
    }
});

document.addEventListener("mouseup", async (e) => {
    if (isDragging && draggedElement) {
        const collided = checkCollisions(draggedElement);
        if (collided) {
            await combineElements(draggedElement, collided);
        }
        
        if (draggedElement && draggedElement.dom) {
            draggedElement.dom.style.zIndex = "";
        }
        isDragging = false;
        draggedElement = null;
    }
});

searchInput.addEventListener("input", renderSidebar);
sortSelect.addEventListener("change", renderSidebar);
if (wordValue) wordValue.addEventListener("input", renderSidebar);
if (depthValue) depthValue.addEventListener("input", renderSidebar);
if (recipeFilter) recipeFilter.addEventListener("change", renderSidebar);

// Stats Modal
if (statsBtn) {
    statsBtn.addEventListener("click", () => {
        renderStats();
        statsModal.style.display = "block";
    });
}

if (closeStats) {
    closeStats.addEventListener("click", () => {
        statsModal.style.display = "none";
    });
}

window.addEventListener("click", (event) => {
    if (event.target === statsModal) statsModal.style.display = "none";
});

function renderStats() {
    if (!statsGrid) return;
    
    const total = discoveredElements.length;
    const baseCount = discoveredElements.filter(e => !e.parents).length;
    const craftedCount = total - baseCount;
    
    // Word count stats
    const oneWord = discoveredElements.filter(e => getWordCount(e.name) === 1).length;
    const twoWords = discoveredElements.filter(e => getWordCount(e.name) === 2).length;
    const threeWords = discoveredElements.filter(e => getWordCount(e.name) === 3).length;
    const fourPlusWords = discoveredElements.filter(e => getWordCount(e.name) >= 4).length;
    
    // Depth stats
    const maxDepth = Math.max(...discoveredElements.map(e => e.depth || 0));
    const avgDepth = (discoveredElements.reduce((sum, e) => sum + (e.depth || 0), 0) / total).toFixed(1);
    const deepestElements = discoveredElements.filter(e => e.depth === maxDepth);
    
    // Recipe stats
    const multiRecipe = discoveredElements.filter(e => getRecipeCount(e) > 1).length;
    const totalRecipes = discoveredElements.reduce((sum, e) => sum + getRecipeCount(e), 0);
    
    // Most recent
    const sorted = [...discoveredElements].sort((a, b) => b.time - a.time);
    const mostRecent = sorted.find(e => e.time > 0);
    
    statsGrid.innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${total}</div>
            <div class="stat-label">Total Elements</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${craftedCount}</div>
            <div class="stat-label">Crafted Elements</div>
        </div>
        <div class="stat-card highlight">
            <div class="stat-value">${maxDepth}</div>
            <div class="stat-label">Max Hierarchy Depth</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${avgDepth}</div>
            <div class="stat-label">Avg Hierarchy Depth</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${oneWord}</div>
            <div class="stat-label">1-Word Elements</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${twoWords}</div>
            <div class="stat-label">2-Word Elements</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${threeWords}</div>
            <div class="stat-label">3-Word Elements</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${fourPlusWords}</div>
            <div class="stat-label">4+ Word Elements</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${totalRecipes}</div>
            <div class="stat-label">Total Recipes</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${multiRecipe}</div>
            <div class="stat-label">Multi-Recipe Elements</div>
        </div>
        <div class="stat-card full-width highlight">
            <div class="stat-value">${deepestElements[0]?.emoji || '?'} ${deepestElements[0]?.name || 'None'}</div>
            <div class="stat-label">Deepest Element (Depth ${maxDepth})</div>
        </div>
        ${mostRecent ? `
        <div class="stat-card full-width">
            <div class="stat-value">${mostRecent.emoji} ${mostRecent.name}</div>
            <div class="stat-label">Most Recent Discovery</div>
        </div>
        ` : ''}
    `;
}

clearBtn.addEventListener("click", () => {
    [...instances].forEach(removeInstance);
});

resetBtn.addEventListener("click", () => {
    if (confirm("Reset all progress?")) {
        discoveredElements = [...initialElements];
        saveProgress();
        renderSidebar();
        [...instances].forEach(removeInstance);
    }
});

// Export/Import
const exportBtn = document.getElementById("export-btn");
const importBtn = document.getElementById("import-btn");
const importFile = document.getElementById("import-file");

exportBtn.addEventListener("click", () => {
    const data = {
        version: 1,
        exportDate: new Date().toISOString(),
        elementCount: discoveredElements.length,
        elements: discoveredElements
    };
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = `infinite-craft-save-${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

importBtn.addEventListener("click", () => {
    importFile.click();
});

importFile.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = (event) => {
        try {
            const data = JSON.parse(event.target.result);
            
            if (!data.elements || !Array.isArray(data.elements)) {
                throw new Error("Invalid save file format");
            }
            
            if (confirm(`Import ${data.elementCount || data.elements.length} elements? This will replace your current progress.`)) {
                discoveredElements = data.elements;
                
                // Migration for imported data
                discoveredElements.forEach(el => {
                    if (el.time === undefined) el.time = 0;
                    if (el.depth === undefined) el.depth = 0;
                    if (el.parents === undefined) el.parents = null;
                    if (el.recipes === undefined) {
                        el.recipes = el.parents ? [el.parents] : [];
                    }
                });
                
                saveProgress();
                renderSidebar();
                [...instances].forEach(removeInstance);
                alert("Import successful!");
            }
        } catch (err) {
            alert("Failed to import: " + err.message);
        }
    };
    reader.readAsText(file);
    e.target.value = ""; // Reset for re-import
});

// Init
renderSidebar();
