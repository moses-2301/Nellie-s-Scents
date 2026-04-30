document.addEventListener('DOMContentLoaded', function () {
    var dropdownElements = document.querySelectorAll('.dropdown-toggle');
    dropdownElements.forEach(function (dropdownToggle) {
        dropdownToggle.addEventListener('click', function () {
            var parent = dropdownToggle.closest('.dropdown');
            if (parent) {
                parent.classList.toggle('show');
            }
        });
    });

    var slideshow = document.querySelector('.slideshow-card');
    if (slideshow) {
        var slides = Array.from(slideshow.querySelectorAll('.slide'));
        var current = 0;
        var prevButton = slideshow.querySelector('.slide-prev');
        var nextButton = slideshow.querySelector('.slide-next');

        function showSlide(index) {
            slides.forEach(function (slide, slideIndex) {
                slide.classList.toggle('active', slideIndex === index);
            });
        }

        function nextSlide() {
            current = (current + 1) % slides.length;
            showSlide(current);
        }

        function prevSlide() {
            current = (current - 1 + slides.length) % slides.length;
            showSlide(current);
        }

        prevButton && prevButton.addEventListener('click', prevSlide);
        nextButton && nextButton.addEventListener('click', nextSlide);

        if (slides.length > 1) {
            setInterval(nextSlide, 6000);
        }
    }
});

function shareProduct(channel) {
    var pageUrl = window.location.href;
    var title = document.querySelector('h1') ? document.querySelector('h1').innerText.trim() : document.title;
    var shareUrl = '#';

    switch (channel) {
        case 'facebook':
            shareUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(pageUrl);
            break;
        case 'whatsapp':
            shareUrl = 'https://api.whatsapp.com/send?text=' + encodeURIComponent(title + ' - ' + pageUrl);
            break;
        case 'twitter':
            shareUrl = 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(title + ' - ' + pageUrl);
            break;
        case 'instagram':
            shareUrl = 'https://www.instagram.com/share?url=' + encodeURIComponent(pageUrl) + '&quote=' + encodeURIComponent(title);
            break;
        default:
            shareUrl = pageUrl;
    }

    window.open(shareUrl, '_blank');
}
