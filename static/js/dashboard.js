document.addEventListener("DOMContentLoaded", () => {
    initializeDashboardPage();
});

function initializeDashboardPage() {
    loadProducts();
    setupEventListeners();
}

// Carrega os produtos e atualiza o dashboard
function loadProducts() {
    fetch("/api/products")
        .then(handleFetchErrors)
        .then(products => {
            populateDashboard(products);
            populateTable(products);
        })
        .catch(error => showErrorInTable("Erro ao carregar os produtos."));
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
        if (product.quantity <= 20) {
            counts.low++;
        } else if (product.quantity <= 50) {
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
// Cria uma linha de produto na tabela
function createProductRow(product) {
    // Formatar os valores como moeda brasileira
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
    if (quantity <= 20) {
        return { statusClass: "text-danger", statusText: "Baixo" };
    } else if (quantity <= 50) {
        return { statusClass: "text-warning", statusText: "Médio" };
    }
    return { statusClass: "text-success", statusText: "OK" };
}

// Mostra um erro na tabela
function showErrorInTable(message) {
    const tableBody = document.getElementById("product-table-body");
    tableBody.innerHTML = `<tr><td colspan="6" class="text-danger">${message}</td></tr>`;
}

// Configura os eventos da página do dashboard
function setupEventListeners() {
    // Botão de Filtro
    const filterButton = document.querySelector('.filter-button');
    if (filterButton) {
        filterButton.addEventListener('click', toggleFilters);
        console.log('Evento de clique registrado no botão de filtro');
    } else {
        console.error('Erro: Botão de filtro não encontrado.');
    }

    // Inputs de Filtro
    document.querySelectorAll('.column-filter').forEach(input => {
        input.addEventListener('input', applyFilters);
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
        const isVisible = table.classList.contains('show-filters');
        console.log('Filtros alternados:', isVisible ? 'Exibindo' : 'Ocultando');
    } else {
        console.error('Erro: Tabela não encontrada.');
    }
}
