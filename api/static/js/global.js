document.addEventListener("DOMContentLoaded", () => {
    // Verifica se está na página do dashboard
    if (document.body.classList.contains('dashboard-page')) {
        initializeDashboardPage();
    }
    // Aplica formatação de moeda
    applyCurrencyFormatting('.currency');
});

// Função global para formatar valores como moeda brasileira (R$)
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);''
}

// Aplica formatação automática em campos com classe específica
function applyCurrencyFormatting(selector) {
    document.querySelectorAll(selector).forEach(input => {
        input.addEventListener('input', () => {
            let numericValue = input.value.replace(/\D/g, ''); // Remove caracteres não numéricos
            if (numericValue) {
                input.value = formatCurrency(parseFloat(numericValue) / 100);
            } else {
                input.value = ''; // Limpa o campo se não houver número
            }
        });
    });
}

// Adiciona formatação e validação no envio do formulário
document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", (event) => {
            const priceInput = document.querySelector("#product-unit-price");
            if (priceInput) {
                // Limpa caracteres como "R$" e espaços antes de enviar
                priceInput.value = priceInput.value
                    .replace("R$", "")
                    .replace(/\s/g, "")
                    .replace(",", ".");
            }
        });
    }
});
