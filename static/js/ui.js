// ui.js - 모든 DOM 조작 및 UI 업데이트 함수

function getScoreSymbol(score) {
    const numericScore = parseFloat(score);
    if (numericScore === Infinity || isNaN(numericScore)) return 'N/A';
    if (numericScore < 0) return 'X';
    if (numericScore > 1) return 'O';
    if (numericScore > 0.5) return '△';
    return 'X';
}

function populateRow(tableBody, card) {
    const row = tableBody.insertRow();
    row.dataset.cardName = card.name;

    if (card.adjusted_count > card.original_adjusted_count) {
        row.className = 'count-increased';
    } else if (card.adjusted_count < card.original_adjusted_count) {
        row.className = 'count-decreased';
    }

    row.insertCell().textContent = card.name;
    row.insertCell().textContent = card.average;
    row.insertCell().textContent = card.original_adjusted_count;

    const countCell = row.insertCell();
    countCell.innerHTML = `
        <button class="adjust-btn" data-action="decrease" data-card-name="${card.name}">-</button>
        <span>${card.adjusted_count}</span>
        <button class="adjust-btn" data-action="increase" data-card-name="${card.name}">+</button>
    `;

    row.insertCell().textContent = getScoreSymbol(card.removability_score);
    row.insertCell().textContent = getScoreSymbol(card.addability_score);
}

export function redrawTable(tableBody, deckTotalSpan, currentDeckData) {
    tableBody.innerHTML = '';
    let totalCount = 0;
    currentDeckData.forEach(card => {
        if (card.name === '총 합') return;
        populateRow(tableBody, card);
        totalCount += card.adjusted_count;
    });
    deckTotalSpan.textContent = `총 ${totalCount} / 40 장`;
}

export function sortTable(table, tableBody, deckTotalSpan, currentDeckData, header, doToggle = true) {
    const currentSortOrder = header.classList.contains('sort-asc') ? 'desc' : 'asc';
    const sortOrder = doToggle ? currentSortOrder : (header.classList.contains('sort-asc') ? 'asc' : 'desc');
    const colIndex = Array.from(header.parentNode.children).indexOf(header);

    // 데이터 배열 정렬
    currentDeckData.sort((a, b) => {
        let valA, valB;
        switch(colIndex) {
            case 0: valA = a.name; valB = b.name; break;
            case 1: valA = parseFloat(a.average); valB = parseFloat(b.average); break;
            case 2: valA = a.original_adjusted_count; valB = b.original_adjusted_count; break;
            case 3: valA = a.adjusted_count; valB = b.adjusted_count; break;
            case 4: valA = a.removability_score; valB = b.removability_score; break;
            case 5: valA = a.addability_score; valB = b.addability_score; break;
            default: valA = 0; valB = 0;
        }

        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
    });

    // 헤더 클래스 업데이트
    if(doToggle) {
        table.querySelectorAll('th.sortable').forEach(th => th.className = 'sortable');
        header.classList.add(sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }

    // 정렬된 데이터로 테이블 다시 그리기
    redrawTable(tableBody, deckTotalSpan, currentDeckData);
}
