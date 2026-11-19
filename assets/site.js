(() => {
  const root = document.documentElement;
  const themeButton = document.querySelector(".theme-toggle");

  const setTheme = (theme) => {
    root.dataset.theme = theme;
    localStorage.setItem("paper-theme", theme);
    if (themeButton) {
      themeButton.setAttribute(
        "aria-label",
        theme === "dark" ? "切换到浅色主题" : "切换到深色主题",
      );
      themeButton.setAttribute(
        "title",
        theme === "dark" ? "切换到浅色主题" : "切换到深色主题",
      );
    }
  };

  if (themeButton) {
    setTheme(root.dataset.theme || "light");
    themeButton.addEventListener("click", () => {
      setTheme(root.dataset.theme === "dark" ? "light" : "dark");
    });
  }

  const searchInput = document.querySelector("#post-search");
  const postItems = [...document.querySelectorAll(".post-item")];
  const tagButtons = [...document.querySelectorAll(".tag-filter")];
  const emptyState = document.querySelector("#empty-state");
  const visibleCount = document.querySelector("#visible-count");
  let activeTag = "all";

  const updatePosts = () => {
    if (!searchInput || postItems.length === 0) return;
    const query = searchInput.value.trim().toLowerCase();
    let shown = 0;

    postItems.forEach((item) => {
      const matchesQuery = !query || item.dataset.search.includes(query);
      const matchesTag =
        activeTag === "all" || item.dataset.tag === activeTag;
      const visible = matchesQuery && matchesTag;
      item.hidden = !visible;
      if (visible) shown += 1;
    });

    if (visibleCount) visibleCount.textContent = String(shown);
    if (emptyState) emptyState.hidden = shown !== 0;
  };

  if (searchInput) {
    searchInput.addEventListener("input", updatePosts);
  }

  tagButtons.forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.classList.contains("is-active")),
    );
    button.addEventListener("click", () => {
      activeTag = button.dataset.tag;
      tagButtons.forEach((item) => {
        const active = item === button;
        item.classList.toggle("is-active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      updatePosts();
    });
  });

  const progressBar = document.querySelector("#reading-progress-bar");
  if (progressBar) {
    const updateProgress = () => {
      const available =
        document.documentElement.scrollHeight - window.innerHeight;
      const progress = available > 0 ? window.scrollY / available : 0;
      progressBar.style.transform = `scaleX(${Math.min(1, Math.max(0, progress))})`;
    };
    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
  }

  const copyButton = document.querySelector("[data-copy-link]");
  if (copyButton) {
    copyButton.addEventListener("click", async () => {
      const label = copyButton.querySelector("span");
      const original = label ? label.textContent : "";
      try {
        await navigator.clipboard.writeText(window.location.href);
        if (label) label.textContent = "链接已复制";
      } catch {
        if (label) label.textContent = "复制失败";
      }
      window.setTimeout(() => {
        if (label) label.textContent = original;
      }, 1800);
    });
  }

})();
