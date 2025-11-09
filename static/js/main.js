
// --- DOM 요소 및 상태 변수 ---
const postSelect = document.getElementById('post_select_elm');
const deckSelect = document.getElementById('deckname_select_elm');
const table = document.getElementById('card_analysis_table');
const tableBody = table.querySelector('tbody');
const deckTotalSpan = document.getElementById('deck-total');
let currentDeckData = []; // 현재 덱 데이터를 저장하는 전역 변수
const epsilon = 1e-6; // 0으로 나누기 오류 방지를 위한 작은 값

// --- API 및 데이터 핸들링 ---

/**
 * 주어진 포스트와 덱에 대한 분석 데이터를 가져와 테이블을 업데이트합니다.
 * @param {string} postUrl - 분석할 포스트의 URL.
 * @param {string} deckName - 분석할 덱의 이름.
 */
function fetchAnalysis(postUrl, deckName) {
    fetch(`/get_deck_analysis?url=${encodeURIComponent(postUrl)}&deck_name=${encodeURIComponent(deckName)}`)
        .then(response => response.json())
        .then(data => updateTable(data))
        .catch(error => console.error('분석 데이터 로딩 오류:', error));
}

/**
 * 서버로부터 받은 데이터로 클라이언트 사이드 데이터 저장소를 초기화합니다.
 * @param {Array<Object>} data - 서버로부터 받은 카드 데이터 객체의 배열.
 */
function updateTable(data) {
    currentDeckData = data.filter(c => c.name !== '총 합').map(card => ({
        ...card,
        original_adjusted_count: parseInt(card.adjusted_count, 10), // 최초 추천값 저장
        adjusted_count: parseInt(card.adjusted_count, 10)      // 사용자가 수정할 값
    }));
    recalculateScores();
    redrawTable();
}

// --- 핵심 로직 ---

/**
 * 주어진 카드 카운트 배열에 대한 전체 통계적 패널티를 계산합니다.
 * @param {Array<number>} deckCounts - 카드 카운트 배열.
 * @returns {number} 총 패널티 점수.
 */
function calculatePenalty(deckCounts) {
    let penalty = 0;
    for (let i = 0; i < currentDeckData.length; i++) {
        const card = currentDeckData[i];
        if (!card.average) continue;
        const delta = deckCounts[i] - parseFloat(card.average);
        const std_dev = parseFloat(card.std_dev);
        penalty += ((delta / (std_dev + epsilon)) ** 2);
    }
    return penalty;
}

/**
 * 현재 덱 상태를 기준으로 모든 카드의 추가/제거 점수를 다시 계산합니다.
 */
function recalculateScores() {
    const currentCounts = currentDeckData.map(c => c.adjusted_count);
    currentDeckData.forEach((card, i) => {
        if (!card.average) return;
        if (card.adjusted_count > 0) {
            const tempCounts = [...currentCounts];
            tempCounts[i]--;
            const penalty = calculatePenalty(tempCounts);
            card.removability_score = penalty > 0 ? 1 / penalty : Infinity;
        } else {
            card.removability_score = -1;
        }
        if (card.adjusted_count < 3) {
            const tempCounts = [...currentCounts];
            tempCounts[i]++;
            const penalty = calculatePenalty(tempCounts);
            card.addability_score = penalty > 0 ? 1 / penalty : Infinity;
        } else {
            card.addability_score = -1;
        }
    });
}

/**
 * 카드 매수를 조정하고 덱의 총 매수를 40장으로 자동 조절합니다.
 * @param {string} cardName - 조정할 카드의 이름.
 * @param {string} action - 수행할 행동 ('increase' 또는 'decrease').
 */
function adjustCardCount(cardName, action) {
    const targetCardIndex = currentDeckData.findIndex(c => c.name === cardName);
    if (targetCardIndex === -1) return;

    const baseCounts = currentDeckData.map(c => c.adjusted_count);

    if (action === 'increase') {
        if (baseCounts[targetCardIndex] >= 3) return;
        
        let minPenalty = Infinity;
        let bestCandidateIndex = -1;

        // 모든 카드를 대상으로 최적의 제거 카드를 탐색
        for (let i = 0; i < baseCounts.length; i++) {
            if (i === targetCardIndex || baseCounts[i] <= 0) continue;
            
            const tempCounts = [...baseCounts];
            tempCounts[targetCardIndex]++;
            tempCounts[i]--;
            const penalty = calculatePenalty(tempCounts);

            if (penalty < minPenalty) {
                minPenalty = penalty;
                bestCandidateIndex = i;
            }
        }

        if (bestCandidateIndex !== -1) {
            currentDeckData[targetCardIndex].adjusted_count++;
            currentDeckData[bestCandidateIndex].adjusted_count--;
        }

    } else if (action === 'decrease') {
        if (baseCounts[targetCardIndex] <= 0) return;

        let minPenalty = Infinity;
        let bestCandidateIndex = -1;

        // 모든 카드를 대상으로 최적의 추가 카드를 탐색
        for (let i = 0; i < baseCounts.length; i++) {
            if (i === targetCardIndex || baseCounts[i] >= 3) continue;

            const tempCounts = [...baseCounts];
            tempCounts[targetCardIndex]--;
            tempCounts[i]++;
            const penalty = calculatePenalty(tempCounts);

            if (penalty < minPenalty) {
                minPenalty = penalty;
                bestCandidateIndex = i;
            }
        }
        
        if (bestCandidateIndex !== -1) {
            currentDeckData[targetCardIndex].adjusted_count--;
            currentDeckData[bestCandidateIndex].adjusted_count++;
        }
    }
    
    recalculateScores();
    redrawTable();
}

// --- DOM 및 UI ---

/**
 * 숫자 점수를 화면에 표시할 심볼(O, △, X)로 변환합니다.
 * @param {number} score - 변환할 점수.
 * @returns {string} 표시용 심볼.
 */
function getScoreSymbol(score) {
    const numericScore = parseFloat(score);
    if (numericScore === Infinity || isNaN(numericScore)) return 'N/A';
    if (numericScore < 0) return 'X';
    if (numericScore > 1) return 'O';
    if (numericScore > 0.5) return '△';
    return 'X';
}

/**
 * `currentDeckData`의 현재 상태를 기반으로 테이블 전체를 다시 그립니다.
 */
function redrawTable() {
    const currentSortHeader = table.querySelector('th.sort-asc, th.sort-desc');
    // 정렬 상태가 활성화된 경우, 데이터를 다시 정렬하여 그림
    if (currentSortHeader) {
        sortTable(currentSortHeader, false);
    } else {
        tableBody.innerHTML = '';
        let totalCount = 0;
        currentDeckData.forEach(card => {
            if (card.name === '총 합') return;
            populateRow(card);
            totalCount += card.adjusted_count;
        });
        deckTotalSpan.textContent = `총 ${totalCount} / 40 장`;
    }
}

/**
 * 테이블에 단일 행을 생성하고 데이터를 채웁니다.
 * @param {Object} card - 행에 대한 카드 데이터 객체.
 */
function populateRow(card) {
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

/**
 * 테이블 데이터를 정렬하고 다시 그리기를 트리거합니다.
 * @param {HTMLElement} header - 클릭된 테이블 헤더 요소.
 * @param {boolean} [doToggle=true] - 정렬 방향을 토글할지 여부.
 */
function sortTable(header, doToggle = true) {
    const currentSortOrder = header.classList.contains('sort-asc') ? 'desc' : 'asc';
    const sortOrder = doToggle ? currentSortOrder : (header.classList.contains('sort-asc') ? 'asc' : 'desc');
    const colIndex = Array.from(header.parentNode.children).indexOf(header);

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

    if(doToggle) {
        table.querySelectorAll('th.sortable').forEach(th => th.className = 'sortable');
        header.classList.add(sortOrder === 'asc' ? 'sort-asc' : 'sort-desc');
    }

    tableBody.innerHTML = '';
    let totalCount = 0;
    currentDeckData.forEach(card => {
        populateRow(card);
        totalCount += card.adjusted_count;
    });
    deckTotalSpan.textContent = `총 ${totalCount} / 40 장`;
}

// --- 이벤트 리스너 ---

// 조정 버튼에 대한 위임된 이벤트 리스너
tableBody.addEventListener('click', function(e) {
    if (e.target && e.target.classList.contains('adjust-btn')) {
        const action = e.target.dataset.action;
        const cardName = e.target.dataset.cardName;
        adjustCardCount(cardName, action);
    }
});

// 테이블 정렬을 위한 이벤트 리스너
table.querySelectorAll('th.sortable').forEach(header => {
    header.addEventListener('click', () => sortTable(header));
});

// 포스트 선택 드롭다운을 위한 이벤트 리스너
postSelect.addEventListener('change', function() {
    const selectedPostUrl = this.value;
    fetch(`/get_deck_names_for_post?url=${encodeURIComponent(selectedPostUrl)}`)
        .then(response => response.json())
        .then(deckNames => {
            deckSelect.innerHTML = '';
            deckNames.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                deckSelect.appendChild(option);
            });
            if (deckNames.length > 0) {
                fetchAnalysis(selectedPostUrl, deckNames[0]);
            }
        })
        .catch(error => console.error('덱 이름 로딩 오류:', error));
});

// 덱 선택 드롭다운을 위한 이벤트 리스너
deckSelect.addEventListener('change', function() {
    const selectedDeckName = this.value;
    const selectedPostUrl = postSelect.value;
    fetchAnalysis(selectedPostUrl, selectedDeckName);
});

// --- 초기 로드 ---
fetchAnalysis(postSelect.value, deckSelect.value);

/**
 * 덱 이름에서 클래스 ID를 추출합니다.
 * @param {string} deckName - 분석할 덱의 이름.
 * @returns {number|null} 클래스 ID 또는 찾지 못한 경우 null.
 */
function getClassIdFromName(deckName) {
    const classMap = {
        'E': 1,
        'R': 2,
        'W': 3,
        'D': 4,
        'Ni': 5,
        'B': 6,
        'Nm': 7
    };

    for (const key in classMap) {
        if (deckName.includes(key)) {
            return classMap[key];
        }
    }
    return null; // 클래스를 찾지 못한 경우
}

// 덱 코드 복사 버튼 이벤트 리스너
document.getElementById('copy-deck-button').addEventListener('click', function() {
    const deckName = deckSelect.value;
    const classId = getClassIdFromName(deckName);

    if (classId === null) {
        alert('덱 이름에서 클래스를 식별할 수 없습니다. 덱 코드 생성이 정확하지 않을 수 있습니다.');
        return;
    }

    const deckForApi = [];
    currentDeckData.forEach(card => {
        for (let i = 0; i < card.adjusted_count; i++) {
            deckForApi.push(card.name);
        }
    });

    fetch('/generate_deck_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ deck: deckForApi, class_id: classId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.deck_code) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(data.deck_code).then(() => {
                    const feedback = document.getElementById('copy-feedback');
                    feedback.textContent = '덱 코드가 클립보드에 복사되었습니다!';
                    feedback.style.visibility = 'visible';
                    setTimeout(() => {
                        feedback.style.visibility = 'hidden';
                    }, 2000);
                }).catch(err => {
                    console.error('클립보드 복사 실패:', err);
                    alert('클립보드 복사에 실패했습니다.');
                });
            } else {
                alert('클립보드 기능이 지원되지 않는 브라우저입니다.');
            }
        } else {
            alert('덱 코드 생성에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
        }
    })
    .catch(error => {
        console.error('덱 코드 생성 API 호출 오류:', error);
        alert('덱 코드 생성 중 서버와 통신하는 데 실패했습니다.');
    });
});
