document.addEventListener("DOMContentLoaded", () => {
    applyCurrencyFormatting('.currency');
});

// Função global para formatar valores como moeda brasileira (R$)
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
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
