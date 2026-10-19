/**
 * S&C ACADEMY (에스앤씨학원) - 메인 스크립트
 * 간결하고 가벼운 바닐라 JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. 헤더 스크롤 상태 및 맨 위로 가기 버튼 관리
  const header = document.getElementById('header');
  const backToTopBtn = document.getElementById('backToTop');

  const handleScroll = () => {
    const scrollY = window.scrollY;

    // 헤더 그림자 효과
    if (scrollY > 30) {
      header.classList.add('scrolled');
    } else {
      header.classList.remove('scrolled');
    }

    // 맨 위로 가기 버튼 표시/숨김
    if (scrollY > 400) {
      backToTopBtn.classList.add('visible');
    } else {
      backToTopBtn.classList.remove('visible');
    }
  };

  window.addEventListener('scroll', handleScroll, { passive: true });
  handleScroll(); // 초기 로드 시 체크

  // 맨 위로 가기 버튼 클릭 시
  if (backToTopBtn) {
    backToTopBtn.addEventListener('click', () => {
      window.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    });
  }

  // 2. 모바일 네비게이션 메뉴 토글
  const mobileToggle = document.getElementById('mobileToggle');
  const siteNav = document.getElementById('siteNav');
  const navLinks = document.querySelectorAll('.nav-link');

  const closeMobileMenu = () => {
    if (mobileToggle && siteNav) {
      mobileToggle.classList.remove('active');
      mobileToggle.setAttribute('aria-expanded', 'false');
      siteNav.classList.remove('open');
    }
  };

  if (mobileToggle && siteNav) {
    mobileToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = siteNav.classList.toggle('open');
      mobileToggle.classList.toggle('active', isOpen);
      mobileToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });

    // 메뉴 링크 클릭 시 모바일 메뉴 자동 닫기
    navLinks.forEach((link) => {
      link.addEventListener('click', () => {
        closeMobileMenu();
      });
    });

    // 메뉴 바깥 클릭 시 닫기
    document.addEventListener('click', (e) => {
      if (!siteNav.contains(e.target) && !mobileToggle.contains(e.target)) {
        closeMobileMenu();
      }
    });

    // ESC 키 누를 시 닫기
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && siteNav.classList.contains('open')) {
        closeMobileMenu();
      }
    });
  }

  // 3. 스크롤스파이 (Scrollspy): 현재 섹션 감지하여 네비게이션 링크 활성화
  const sections = document.querySelectorAll('main section[id]');

  const handleScrollSpy = () => {
    const scrollPosition = window.scrollY + 120;

    sections.forEach((section) => {
      const top = section.offsetTop;
      const height = section.offsetHeight;
      const id = section.getAttribute('id');
      const targetNavLink = document.querySelector(`.site-nav a[href="#${id}"]`);

      if (scrollPosition >= top && scrollPosition < top + height) {
        if (targetNavLink) {
          navLinks.forEach((link) => link.classList.remove('active'));
          targetNavLink.classList.add('active');
        }
      }
    });
  };

  window.addEventListener('scroll', handleScrollSpy, { passive: true });
});

/* 블로그 슬라이드: 실제 썸네일 우선, 실패하면 학원 공통 이미지 */
document.addEventListener('DOMContentLoaded', function () {
  const carousel = document.getElementById('highlightCarousel');
  if (!carousel) return;
  let slides = [{ title: '훈민정음 28자는 왜 24자가 됐을까? 사라진 네 글자의 흔적', url: 'https://blog.naver.com/hannak74/224433289896', image: '', tag: 'PICK' }];
  let pos = 0;
  const link = document.getElementById('highlightLink'), img = document.getElementById('highlightImage');
  const empty = document.getElementById('highlightNoImage'), title = document.getElementById('highlightTitle');
  const tag = document.getElementById('highlightTag'), count = document.getElementById('highlightCount');
  function render() {
    const s = slides[pos]; link.href = s.url; title.textContent = s.title; tag.textContent = s.tag;
    count.textContent = (pos + 1) + ' / ' + slides.length;
    const fallback = 'images/blog-fallback.png';
    const source = (typeof s.image === 'string' && s.image.trim()) ? s.image.trim() : fallback; img.hidden = false; empty.hidden = true;
    img.alt = s.title + ' 대표 이미지';
    img.onerror = function () {
      // Never loop if even the local fallback is missing.
      if (img.src.endsWith('/' + fallback)) { img.hidden = true; empty.hidden = false; return; }
      img.onerror = function () { img.hidden = true; empty.hidden = false; };
      img.src = fallback;
    };
    img.src = source;
  }
  document.getElementById('highlightPrev').addEventListener('click', function () { pos = (pos + slides.length - 1) % slides.length; render(); });
  document.getElementById('highlightNext').addEventListener('click', function () { pos = (pos + 1) % slides.length; render(); });
  fetch('data/blog-posts.json', { cache: 'no-store' }).then(r => { if (!r.ok) throw Error('blog data'); return r.json(); }).then(data => {
    if (!Array.isArray(data.posts)) return;
    const valid = data.posts.filter(p => p && p.title && /^https:\/\/(?:m\.)?blog\.naver\.com\/hannak74\/\d+/.test(p.url)).slice(0, 3);
    if (valid.length) { slides = valid; pos = 0; render(); }
  }).catch(() => { });
  render();
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    setInterval(function () { if (!document.hidden && slides.length > 1) { pos = (pos + 1) % slides.length; render(); } }, 5500);
  }
});

/* 브랜드 상세 안내: 한 번에 하나만 펼치기 */
document.addEventListener('DOMContentLoaded', function () {
  var buttons = Array.from(document.querySelectorAll('.program-expand'));
  buttons.forEach(function (button) {
    button.addEventListener('click', function () {
      var shouldOpen = button.getAttribute('aria-expanded') !== 'true';
      buttons.forEach(function (other) { other.setAttribute('aria-expanded', 'false'); document.getElementById(other.getAttribute('aria-controls')).hidden = true; });
      if (shouldOpen) { button.setAttribute('aria-expanded', 'true'); document.getElementById(button.getAttribute('aria-controls')).hidden = false; }
    });
  });
});
