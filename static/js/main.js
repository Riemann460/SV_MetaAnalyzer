// main.js - 앱 로직, 상태 관리, 이벤트 핸들링
import * as ui from './ui.js';

// --- DOM 요소 및 상태 변수 ---
const postSelect = document.getElementById('post_select_elm');
const deckSelect = document.getElementById('deckname_select_elm');
const table = document.getElementById('card_analysis_table');
const tableBody = table.querySelector('tbody');
const deckTotalSpan = document.getElementById('deck-total');

let currentDeckData = []; // 현재 덱 데이터를 저장하는 전역 변수
const epsilon = 1e-6; // 0으로 나누기 오류 방지를 위한 작은 값

// --- API 및 데이터 핸들링 ---
function fetchAnalysis(postUrl, deckName) {
    fetch(`/get_deck_analysis?url=${encodeURIComponent(postUrl)}&deck_name=${encodeURIComponent(deckName)}`)
        .then(response => response.json())
        .then(data => updateTable(data))
        .catch(error => console.error('분석 데이터 로딩 오류:', error));
}

function updateTable(data) {
    currentDeckData = data.filter(c => c.name !== '총 합').map(card => ({
        ...card,
        original_adjusted_count: parseInt(card.adjusted_count, 10),
        adjusted_count: parseInt(card.adjusted_count, 10)
    }));
    recalculateScores();
    // Call redrawTable from ui.js
    const currentSortHeader = table.querySelector('th.sort-asc, th.sort-desc');
    if (currentSortHeader) {
        ui.sortTable(table, tableBody, deckTotalSpan, currentDeckData, currentSortHeader, false);
    } else {
        ui.redrawTable(tableBody, deckTotalSpan, currentDeckData);
    }
}

// --- 핵심 로직 ---
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

function adjustCardCount(cardName, action) {
    const targetCardIndex = currentDeckData.findIndex(c => c.name === cardName);
    if (targetCardIndex === -1) return;

    const baseCounts = currentDeckData.map(c => c.adjusted_count);

    if (action === 'increase') {
        if (baseCounts[targetCardIndex] >= 3) return;
        
        let minPenalty = Infinity;
        let bestCandidateIndex = -1;

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
    // Call redrawTable from ui.js
    ui.redrawTable(tableBody, deckTotalSpan, currentDeckData);
}

function getClassIdFromName(deckName) {
    const classMap = { 'E': 1, 'R': 2, 'W': 3, 'D': 4, 'Ni': 5, 'B': 6, 'Nm': 7 };
    for (const key in classMap) {
        if (deckName.includes(key)) {
            return classMap[key];
        }
    }
    return null;
}

// --- 이벤트 리스너 ---
tableBody.addEventListener('click', function(e) {
    if (e.target && e.target.classList.contains('adjust-btn')) {
        const action = e.target.dataset.action;
        const cardName = e.target.dataset.cardName;
        adjustCardCount(cardName, action);
    }
});

table.querySelectorAll('th.sortable').forEach(header => {
    header.addEventListener('click', () => ui.sortTable(table, tableBody, deckTotalSpan, currentDeckData, header));
});

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

deckSelect.addEventListener('change', function() {
    const selectedDeckName = this.value;
    const selectedPostUrl = postSelect.value;
    fetchAnalysis(selectedPostUrl, selectedDeckName);
});

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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deck: deckForApi, class_id: classId }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.deck_code) {
            navigator.clipboard.writeText(data.deck_code).then(() => {
                const feedback = document.getElementById('copy-feedback');
                feedback.textContent = '덱 코드가 클립보드에 복사되었습니다!';
                feedback.style.visibility = 'visible';
                setTimeout(() => { feedback.style.visibility = 'hidden'; }, 2000);
            }).catch(err => {
                console.error('클립보드 복사 실패:', err);
                alert('클립보드 복사에 실패했습니다.');
            });
        } else {
            alert('덱 코드 생성에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
        }
    })
    .catch(error => {
        console.error('덱 코드 생성 API 호출 오류:', error);
        alert('덱 코드 생성 중 서버와 통신하는 데 실패했습니다.');
    });
});

// --- 초기 로드 ---
fetchAnalysis(postSelect.value, deckSelect.value);