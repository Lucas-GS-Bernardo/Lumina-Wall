document.addEventListener('DOMContentLoaded', function() {
    const lista = document.getElementById('lista-mural');
    
    if (lista) {
        Sortable.create(lista, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            onEnd: function () {
                const ordem = [];
                // Pega o ID de cada card na nova ordem
                document.querySelectorAll('.card').forEach(c => {
                    ordem.push(c.getAttribute('data-id'));
                });

                // Envia para o servidor salvar
                fetch('/reordenar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ordem: ordem })
                })
                .then(res => res.json())
                .then(data => console.log("Nova ordem salva!"));
            }
        });
    }
});

function updateFileName() {
    const input = document.getElementById('arquivo');
    const label = document.getElementById('file-label');
    const labelText = document.getElementById('file-text');
    
    if (input.files.length > 0) {
        // Pega o nome do arquivo
        const fileName = input.files[0].name;
        // Atualiza o texto e adiciona a classe de estilo
        labelText.textContent = fileName;
        label.classList.add('file-selected');
    } else {
        // Volta ao estado original se desmarcar
        labelText.textContent = "Escolher arquivo";
        label.classList.remove('file-selected');
    }
}