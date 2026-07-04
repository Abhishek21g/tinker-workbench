const header = document.querySelector(".site-header");

const updateHeader = () => {
  if (!header) return;
  header.dataset.scrolled = window.scrollY > 10 ? "true" : "false";
};

window.addEventListener("scroll", updateHeader, { passive: true });
updateHeader();
