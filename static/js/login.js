document.addEventListener("DOMContentLoaded", function () {
    setTimeout(function () {
        var flashMessage = document.getElementById("flash-message");
        if (flashMessage) {
            flashMessage.style.transition = "opacity 0.5s";
            flashMessage.style.opacity = "0";
            setTimeout(() => flashMessage.style.display = "none", 500);
        }
    }, 3500);
});