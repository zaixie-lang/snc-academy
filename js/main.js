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
