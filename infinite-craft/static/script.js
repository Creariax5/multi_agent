const initialElements = [
    { name: "Water", emoji: "💧" },
    { name: "Fire", emoji: "🔥" },
    { name: "Earth", emoji: "🌍" },
    { name: "Wind", emoji: "💨" }
];

let discoveredElements = JSON.parse(localStorage.getItem("infinite-craft-elements")) || initialElements;
let instances = [];
let isDragging = false;
let draggedElement = null;
let dragOffsetX = 0;
let dragOffsetY = 0;

const craftingArea = document.getElementById("crafting-area");
const elementsList = document.getElementById("elements-list");
const searchInput = document.getElementById("search-input");
const clearBtn = document.getElementById("clear-btn");
const resetBtn = document.getElementById("reset-btn");

function saveProgress() {
    localStorage.setItem("infinite-craft-elements", JSON.stringify(discoveredElements));
}

function renderSidebar() {
    elementsList.innerHTML = "";
    const filter = searchInput.value.toLowerCase();
    
    discoveredElements
        .filter(el => el.name.toLowerCase().includes(filter))
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(el => {
            const div = document.createElement("div");
            div.className = "element";
            div.innerHTML = `<span class="emoji">${el.emoji}</span> <span class="name">${el.name}</span>`;
            div.draggable = true;
            div.addEventListener("dragstart", (e) => {
                e.dataTransfer.setData("application/json", JSON.stringify(el));
                e.dataTransfer.effectAllowed = "copy";
            });
            elementsList.appendChild(div);
        });
}

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
        
        const newElement = { name: data.result, emoji: data.emoji };
        
        // Check if new discovery
        const exists = discoveredElements.some(e => e.name === newElement.name);
        if (!exists) {
            discoveredElements.push(newElement);
            saveProgress();
            renderSidebar();
        }

        const newInstance = createInstance(newElement, newX, newY);
        if (!exists) {
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

// Init
renderSidebar();
