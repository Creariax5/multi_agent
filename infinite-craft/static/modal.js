// Modal elements
const modal = document.getElementById("element-modal");
const closeModal = document.querySelector(".close-modal");
const modalTitle = document.getElementById("modal-title");
const modalEmoji = document.getElementById("modal-emoji");
const modalDate = document.getElementById("modal-date");
const modalDepth = document.getElementById("modal-depth");
const craftingTree = document.getElementById("crafting-tree");

function showElementDetails(element) {
    modalTitle.textContent = element.name;
    modalEmoji.textContent = element.emoji;
    modalDate.textContent = element.time === 0 ? "Initial Element" : new Date(element.time).toLocaleString();
    modalDepth.textContent = element.depth;
    
    renderCraftingTree(element);
    modal.style.display = "block";
}

function renderCraftingTree(element) {
    craftingTree.innerHTML = "";
    
    // Use recipes array if available, otherwise fallback to parents
    const recipes = element.recipes && element.recipes.length > 0 
        ? element.recipes 
        : (element.parents ? [element.parents] : []);

    if (recipes.length === 0) {
        const msg = document.createElement("div");
        msg.textContent = "Base Element (No Recipe)";
        msg.style.textAlign = "center";
        msg.style.padding = "20px";
        craftingTree.appendChild(msg);
        return;
    }

    recipes.forEach((recipe, index) => {
        const recipeContainer = document.createElement("div");
        recipeContainer.className = "recipe-container";
        
        if (recipes.length > 1) {
            const title = document.createElement("h4");
            title.textContent = `Recipe ${index + 1}`;
            title.style.textAlign = "left";
            title.style.color = "#888";
            title.style.marginBottom = "10px";
            recipeContainer.appendChild(title);
        }

        // Build flat list of rows
        const tempElement = { ...element, parents: recipe };
        buildTreeRows(recipeContainer, tempElement, 0, 3);
        
        craftingTree.appendChild(recipeContainer);
    });
}

function buildTreeRows(container, element, depth, maxDepth) {
    const row = document.createElement("div");
    row.className = `tree-row depth-${Math.min(depth, 4)}`;
    row.style.setProperty('--depth', depth);
    
    const hasParents = element.parents && element.parents.length === 2;
    const isCollapsed = depth >= maxDepth && hasParents;
    
    // Toggle button
    const toggle = document.createElement("div");
    toggle.className = "tree-toggle";
    
    if (hasParents) {
        toggle.textContent = isCollapsed ? "+" : "−";
        toggle.onclick = () => toggleRow(row, element, depth, maxDepth, container);
    } else {
        toggle.classList.add("placeholder");
    }
    row.appendChild(toggle);
    
    // Element display
    const elementDiv = document.createElement("span");
    elementDiv.className = "tree-element";
    elementDiv.innerHTML = `<span class="emoji">${element.emoji}</span> ${element.name}`;
    row.appendChild(elementDiv);
    
    // Show parents inline
    if (hasParents) {
        const arrow = document.createElement("span");
        arrow.className = "tree-arrow";
        arrow.textContent = "←";
        row.appendChild(arrow);
        
        const parentsDiv = document.createElement("span");
        parentsDiv.className = "tree-parents";
        
        const p1 = discoveredElements.find(e => e.name === element.parents[0]) || { name: element.parents[0], emoji: "❓" };
        const p2 = discoveredElements.find(e => e.name === element.parents[1]) || { name: element.parents[1], emoji: "❓" };
        
        parentsDiv.innerHTML = `
            <span class="tree-parent-element">${p1.emoji} ${p1.name}</span>
            <span class="tree-plus">+</span>
            <span class="tree-parent-element">${p2.emoji} ${p2.name}</span>
        `;
        row.appendChild(parentsDiv);
    }
    
    // Store data for expand/collapse
    row.dataset.expanded = isCollapsed ? "false" : "true";
    row.dataset.elementName = element.name;
    
    container.appendChild(row);
    
    // Add children rows if not collapsed
    if (hasParents && !isCollapsed) {
        const parent1 = discoveredElements.find(e => e.name === element.parents[0]) || { name: element.parents[0], emoji: "❓", parents: null };
        const parent2 = discoveredElements.find(e => e.name === element.parents[1]) || { name: element.parents[1], emoji: "❓", parents: null };
        
        // Mark children rows
        const childWrapper = document.createElement("div");
        childWrapper.className = "tree-children-wrapper";
        childWrapper.dataset.parentRow = element.name;
        
        buildTreeRows(childWrapper, parent1, depth + 1, maxDepth);
        buildTreeRows(childWrapper, parent2, depth + 1, maxDepth);
        
        container.appendChild(childWrapper);
        row._childWrapper = childWrapper;
    }
}

function toggleRow(row, element, depth, maxDepth, container) {
    const toggle = row.querySelector(".tree-toggle");
    const isExpanded = row.dataset.expanded === "true";
    
    if (isExpanded) {
        // Collapse: remove children wrapper
        if (row._childWrapper) {
            row._childWrapper.remove();
            row._childWrapper = null;
        }
        toggle.textContent = "+";
        row.dataset.expanded = "false";
    } else {
        // Expand: add children
        const parent1 = discoveredElements.find(e => e.name === element.parents[0]) || { name: element.parents[0], emoji: "❓", parents: null };
        const parent2 = discoveredElements.find(e => e.name === element.parents[1]) || { name: element.parents[1], emoji: "❓", parents: null };
        
        const childWrapper = document.createElement("div");
        childWrapper.className = "tree-children-wrapper";
        
        buildTreeRows(childWrapper, parent1, depth + 1, maxDepth + 3);
        buildTreeRows(childWrapper, parent2, depth + 1, maxDepth + 3);
        
        // Insert after the current row
        row.after(childWrapper);
        row._childWrapper = childWrapper;
        
        toggle.textContent = "−";
        row.dataset.expanded = "true";
    }
}

// Event Listeners for Modal
if (closeModal) {
    closeModal.onclick = () => modal.style.display = "none";
}

window.onclick = (event) => {
    if (event.target == modal) modal.style.display = "none";
}
