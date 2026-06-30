(function () {
  function fallbackCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-1000px";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }
  }

  function setButtonState(button, label) {
    var original = button.dataset.originalLabel || button.textContent;
    button.dataset.originalLabel = original;
    button.textContent = label;
    window.setTimeout(function () {
      button.textContent = original;
    }, 1600);
  }

  function copyText(button) {
    var targetId = button.getAttribute("data-copy-target");
    var target = document.getElementById(targetId);
    if (!target) {
      setButtonState(button, "Missing");
      return;
    }
    var text = target.textContent;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(
        function () {
          setButtonState(button, "Copied");
        },
        function () {
          fallbackCopy(text);
          setButtonState(button, "Copied");
        }
      );
      return;
    }
    fallbackCopy(text);
    setButtonState(button, "Copied");
  }

  document.addEventListener("click", function (event) {
    var button = event.target.closest("[data-copy-target]");
    if (!button) {
      return;
    }
    copyText(button);
  });
})();
