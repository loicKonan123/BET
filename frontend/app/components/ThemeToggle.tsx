"use client";

import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    setLight(document.documentElement.classList.contains("light"));
  }, []);

  function toggle() {
    const isLight = document.documentElement.classList.toggle("light");
    try {
      localStorage.setItem("theme", isLight ? "light" : "dark");
    } catch {}
    setLight(isLight);
  }

  return (
    <button
      onClick={toggle}
      title={light ? "Passer en thème sombre" : "Passer en thème clair"}
      className="material-symbols-outlined p-sm rounded-full hover:bg-primary/10 text-on-surface-variant transition-colors active:scale-95"
    >
      {light ? "dark_mode" : "light_mode"}
    </button>
  );
}
