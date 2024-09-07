let tg = window.Telegram.WebApp;

tg.expand()
tg.headerColor = "#17212b";
tg.MainButton.textColor = "#FFFFFF"
tg.MainButton.color = "#ff3b3b";
tg.MainButton.setText("Закрыть")

const image = document.getElementById("coin");
let scoreElement = document.getElementById("score");
let isRed = false;

try {
    image.onclick = function() {
        let currentScore = parseInt(scoreElement.textContent);
        const randomPoints = Math.floor(Math.random() * 3) + 1;
        currentScore += randomPoints;
        scoreElement.textContent = currentScore;
        tg.MainButton.show();
    
    
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
    
    Telegram.WebApp.onEvent("mainButtonClicked", function(){
        let score = parseInt(scoreElement.textContent);
        tg.sendData(score.toString());
        tg.close();
    });
} catch (error) {
    tg.sendData("Ошибка: " + error.message);
}
