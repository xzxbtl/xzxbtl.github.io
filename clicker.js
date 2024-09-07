let tg = window.Telegram.WebApp;

tg.expand()
tg.headerColor = "#17212b";
alert(tg.initDataUnsafe.user.id)

const image = document.getElementById("coin");
let scoreElement = document.getElementById("score");
let isRed = false;

image.onclick = function() {
    let currentScore = parseInt(scoreElement.textContent);
    const randomPoints = Math.floor(Math.random() * 3) + 1;
    currentScore += randomPoints;
    scoreElement.textContent = currentScore;

    if (currentScore % 50 === 0 && !isRed) {
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

    const plusOneElement = document.createElement('span');
    plusOneElement.textContent = `+${randomPoints}`;
    plusOneElement.classList.add('plus-one');

    const position = Math.random() < 0.5 ? 'top' : 'bottom';
    plusOneElement.classList.add(position);

    document.querySelector('.coin-block').appendChild(plusOneElement);

    plusOneElement.addEventListener('animationend', () => {
        document.querySelector('.coin-block').removeChild(plusOneElement);
    });
};

const scaleScore100 = document.createElement('style');
scaleScore100.innerHTML = `
@keyframes scaleScore100 {
    0% { transform: scale(1); color: red; } 
    50% { transform: scale(1.2); color: red; } 
    100% { transform: scale(1); color: white; } 
}
`;
document.head.appendChild(scaleScore100);


Telegram.WebApp.onEvent("image.onclick", function(){
    const score = parseInt(scoreElement.textContent);
    tg.sendData(score); 
});
