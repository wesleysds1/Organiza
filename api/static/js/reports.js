document.addEventListener("DOMContentLoaded", () => {
    fetchProductStatusSummary();
    fetchEntriesByMonth();
    fetchProductsBySupplier();
    fetchTotalSpentByMonth();
});

function fetchProductStatusSummary() {
    fetch("/api/product_status_summary")
        .then(response => response.json())
        .then(data => {
            console.log("Dados recebidos para o gráfico:", data); // Adicione log para verificar
            const ctx = document.getElementById("chart1").getContext("2d");
            new Chart(ctx, {
                type: "pie",
                data: {
                    labels: ["Baixo (Vermelho)", "Médio (Amarelo)", "OK (Verde)"],
                    datasets: [{
                        data: [data.low, data.medium, data.ok],
                        backgroundColor: ["#f03a52", "#f9bb28", "#1ece94"]
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: "top"
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => {
                                    const label = context.label || "";
                                    const value = context.raw || 0;
                                    return `${label}: ${value} produtos`;
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(error => console.error("Erro ao carregar os dados do gráfico:", error));
}

function fetchEntriesByMonth() {
    fetch("/api/entries_by_month")
        .then(response => response.json())
        .then(data => {
            const table = document.getElementById("table2");
            table.innerHTML = `
                <thead>
                    <tr>
                        <th>Mês</th>
                        <th>Entradas</th>
                        <th>Valor Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(row => {
                        const month = new Date(row.month).toLocaleString("pt-BR", { month: "long", year: "numeric" });
                        const totalValue = isNaN(row.total_value) ? "R$ 0,00" : `R$ ${parseFloat(row.total_value).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
                        return `
                            <tr>
                                <td>${month}</td>
                                <td>${row.total_entries}</td>
                                <td>${totalValue}</td>
                            </tr>
                        `;
                    }).join("")}
                </tbody>
            `;
        })
        .catch(error => console.error("Erro ao carregar entradas por mês:", error));
}

function fetchProductsBySupplier() {
    fetch("/api/products_by_supplier")
        .then(response => response.json())
        .then(data => {
            const tableBody = document.querySelector("#table3 tbody");
            tableBody.innerHTML = data.map(row => `
                <tr>
                    <td>${row.supplier}</td>
                    <td>${row.product_count}</td>
                </tr>
            `).join("");
        });
}

function fetchTotalSpentByMonth() {
    fetch("/api/total_spent_by_month")
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById("chart4").getContext("2d");
            new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.map(row => row.month),
                    datasets: [{
                        label: "Gasto Total (R$)",
                        data: data.map(row => row.total_spent),
                        backgroundColor: "#007bff"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "top"
                        }
                    }
                }
            });
        });
}
