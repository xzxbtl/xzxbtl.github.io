let tg = window.Telegram.WebApp;

tg.expand()
tg.headerColor = "#615b5b";
alert(tg.initData)

const image = document.getElementById("coin");
let scoreElement = document.getElementById("score"); 
let isRed = false;

image.onclick = function() {
    let currentScore = parseInt(scoreElement.textContent);
    currentScore += 1;
    scoreElement.textContent = currentScore; 

    if (currentScore % 20 === 0 && !isRed) {
    scoreElement.style.cssText = `
        color: white;
        animation: scaleScore100 1.5s ease-out; 
    `;
    isRed = true;

    scoreElement.addEventListener('animationend', () => {
        isRed = false;
        scoreElement.style.removeProperty('animation');
    });
    }
};

// Определение анимации scaleScore100
const scaleScore100 = document.createElement('style');
scaleScore100.innerHTML = `
@keyframes scaleScore100 {
    0% { transform: scale(1); color: red; } 
    50% { transform: scale(1.2); color: red; } 
    100% { transform: scale(1); color: white; } 
}
`;
document.head.appendChild(scaleScore100); 
