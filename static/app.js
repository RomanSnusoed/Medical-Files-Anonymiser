document.addEventListener("DOMContentLoaded", () => {
  initialiseCopyButtons();
  initialiseDropzone();
  initialiseAnimations();
});

function initialiseCopyButtons() {
  const buttons = document.querySelectorAll("[data-copy-target]");
  buttons.forEach((button) => {
    const defaultLabel = button.dataset.label || button.textContent.trim() || "Copy";
    button.addEventListener("click", async () => {
      const targetId = button.getAttribute("data-copy-target");
      const target = document.getElementById(targetId);
      if (!target) {
        return;
      }

      const text = target.innerText || target.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
        showCopySuccess(button, defaultLabel);
      } catch (error) {
        fallbackCopyText(text, button, defaultLabel);
      }
    });
  });
}

function showCopySuccess(button, defaultLabel) {
  button.classList.add("is-copied");
  button.textContent = "Copied!";
  setTimeout(() => {
    button.classList.remove("is-copied");
    button.textContent = defaultLabel;
  }, 2000);
}

function fallbackCopyText(text, button, defaultLabel) {
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  try {
    document.execCommand("copy");
    showCopySuccess(button, defaultLabel);
  } catch (error) {
    button.textContent = "Unable to copy";
    setTimeout(() => {
      button.textContent = defaultLabel;
    }, 2000);
  } finally {
    document.body.removeChild(textarea);
  }
}

function initialiseDropzone() {
  const dropzone = document.querySelector("[data-dropzone]");
  const input = document.querySelector("[data-file-input]");
  const nameLabel = document.querySelector("[data-file-name]");

  if (!dropzone || !input) {
    return;
  }

  const updateLabel = () => {
    if (input.files && input.files.length > 0) {
      nameLabel.textContent = input.files[0].name;
    } else if (nameLabel.dataset.placeholder) {
      nameLabel.textContent = nameLabel.dataset.placeholder;
    }
  };

  if (nameLabel && !nameLabel.dataset.placeholder) {
    nameLabel.dataset.placeholder = nameLabel.textContent;
  }

  dropzone.addEventListener("click", () => input.click());

  input.addEventListener("change", updateLabel);

  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragover");
    });
  });

  ["dragleave", "dragend", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.remove("is-dragover");
    });
  });

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    if (!event.dataTransfer || !event.dataTransfer.files) {
      return;
    }
    input.files = event.dataTransfer.files;
    updateLabel();
  });
}

function initialiseAnimations() {
  const animatedNodes = document.querySelectorAll("[data-animate-on-load]");
  if (!("IntersectionObserver" in window)) {
    animatedNodes.forEach((node) => node.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    {
      threshold: 0.15,
    }
  );

  animatedNodes.forEach((node) => observer.observe(node));
}
