document.addEventListener("DOMContentLoaded", function () {
    const resizable = document.getElementById("resizeable");
    const sidebar = document.getElementById("sidebar-nav");

    let startX, startSidebarWidth;

    function initResize(e) {
        startX = e.clientX;
        startSidebarWidth = parseInt(
            document.defaultView.getComputedStyle(sidebar).width,
            10
        );

        document.addEventListener("mousemove", startResize, false);
        document.addEventListener("mouseup", stopResize, false);
    }

    function startResize(e) {
        const width = startSidebarWidth + e.clientX - startX;
        sidebar.style.width = `${width}px`;
    }

    function stopResize() {
        document.removeEventListener("mousemove", startResize, false);
        document.removeEventListener("mouseup", stopResize, false);
    }

    resizable.addEventListener("mousedown", initResize, false);
});
