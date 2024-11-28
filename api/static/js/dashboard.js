document.addEventListener("DOMContentLoaded", () => {
    initializeDashboardPage();
});

function initializeDashboardPage() {
    showSkeletonLoaders(); // Mostra os skeleton loaders nos cartões
    showTableSpinner(); // Mostra o spinner na tabela
    loadProducts(); // Carrega os dados da tabela e dos cartões
    setupEventListeners();
}

// Exibe os skeleton loaders nos cartões de resumo
function showSkeletonLoaders() {
    document.querySelectorAll(".card").forEach(card => {
        card.classList.add("d-none");
    });
    document.querySelectorAll(".card-loader").forEach(loader => {
        loader.classList.remove("d-none");
    });
}

// Oculta os skeleton loaders e exibe os cartões com dados reais
function hideSkeletonLoaders() {
    document.querySelectorAll(".card-loader").forEach(loader => {
        loader.classList.add("d-none");
    });
    document.querySelectorAll(".card").forEach(card => {
        card.classList.remove("d-none");
    });
}

// Mostra o spinner na tabela
function showTableSpinner() {
    document.getElementById("spinner").classList.remove("d-none");
    document.getElementById("product-table").classList.add("d-none");
}

// Oculta o spinner da tabela e exibe os dados carregados
function hideTableSpinner() {
    document.getElementById("spinner").classList.add("d-none");
    document.getElementById("product-table").classList.remove("d-none");
}

// Carrega os produtos e atualiza o dashboard
function loadProducts(page = 1) {
    fetch(`/api/products?page=${page}&per_page=10`, {
        headers: {
            "Cache-Control": "no-cache",
        }
    })
        .then(handleFetchErrors)
        .then(products => {
            populateTable(products);
            populateDashboard(products);
            hideSkeletonLoaders(); // Oculta os skeleton loaders
            hideTableSpinner(); // Oculta o spinner da tabela
        })
        .catch(error => {
            console.error("Erro ao carregar produtos:", error);
            showErrorInTable("Erro ao carregar produtos.");
        });
}

// Manipula erros de fetch
function handleFetchErrors(response) {
    if (!response.ok) throw new Error("Erro ao buscar os dados da API");
    return response.json();
}

// Preenche o painel de resumo
function populateDashboard(products) {
    const totalProducts = products.length;
    const stockCounts = countStock(products);

    document.getElementById("total-products").textContent = totalProducts;
    document.getElementById("stock-ok").textContent = stockCounts.ok;
    document.getElementById("stock-medium").textContent = stockCounts.medium;
    document.getElementById("stock-low").textContent = stockCounts.low;
}

// Conta os produtos por status de estoque
function countStock(products) {
    return products.reduce((counts, product) => {
        if (product.quantity <= 15) {
            counts.low++;
        } else if (product.quantity <= 30) {
            counts.medium++;
        } else {
            counts.ok++;
        }
        return counts;
    }, { ok: 0, medium: 0, low: 0 });
}

// Preenche a tabela de produtos
function populateTable(products) {
    const tableBody = document.getElementById("product-table-body");
    tableBody.innerHTML = products.map(product => createProductRow(product)).join('');
}

// Cria uma linha de produto na tabela
function createProductRow(product) {
    const formatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
    const totalValue = formatter.format(product.quantity * product.price);
    const priceFormatted = formatter.format(product.price);
    const { statusClass, statusText } = getProductStatus(product.quantity);

    return `
        <tr>
            <td><a href="/edit_product/${product.id}" class="text-decoration-none">${product.name}</a></td>
            <td>${product.supplier}</td>
            <td>${product.quantity}</td>
            <td>${priceFormatted}</td>
            <td>${totalValue}</td>
            <td class="${statusClass}">${statusText}</td>
        </tr>
    `;
}

// Determina o status do produto baseado na quantidade
function getProductStatus(quantity) {
    if (quantity <= 15) {
        return { statusClass: "text-danger font-weight-bold", statusText: "Baixo" };
    } else if (quantity <= 30) {
        return { statusClass: "text-warning font-weight-bold", statusText: "Médio" };
    }
    return { statusClass: "text-success font-weight-bold", statusText: "OK" };
}

// Mostra um erro na tabela
function showErrorInTable(message) {
    const tableBody = document.getElementById("product-table-body");
    tableBody.innerHTML = `<tr><td colspan="6" class="text-danger">${message}</td></tr>`;
}

// Configura os eventos da página do dashboard
function setupEventListeners() {
    const filterButton = document.querySelector('.filter-button');
    if (filterButton) {
        filterButton.addEventListener('click', toggleFilters);
    }

    document.querySelectorAll('.column-filter').forEach(input => {
        input.addEventListener('input', debounce(applyFilters, 300));
    });
}

// Aplica filtros na tabela
function applyFilters() {
    const filters = Array.from(document.querySelectorAll('.column-filter')).map(input => input.value.toLowerCase());
    const rows = document.querySelectorAll('#product-table-body tr');

    rows.forEach(row => {
        const isVisible = Array.from(row.children).every((cell, index) => {
            const filter = filters[index];
            return !filter || cell.textContent.toLowerCase().includes(filter);
        });
        row.style.display = isVisible ? '' : 'none';
    });
}

// Alterna a exibição dos filtros
function toggleFilters() {
    const table = document.querySelector('.table');
    if (table) {
        table.classList.toggle('show-filters');
    }
}

// Função de debounce para otimizar o filtro
function debounce(func, delay) {
    let debounceTimer;
    return (...args) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => func(...args), delay);
    };
}
