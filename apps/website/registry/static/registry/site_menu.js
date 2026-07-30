(() => {
    "use strict";
    const toggle = document.querySelector("[data-site-menu-toggle]");
    const menu = document.querySelector("[data-site-menu]");
    if (!toggle || !menu) return;

    const headerControls = toggle.closest(".site-header-controls") || document;
    const submenuToggles = [...headerControls.querySelectorAll("[data-nav-submenu-toggle]")];
    const notificationItem = headerControls.querySelector("[data-notification-live]");
    const notificationToggle = notificationItem?.querySelector(".notification-menu-toggle");
    const notificationList = notificationItem?.querySelector(".notification-preview-list");
    const notificationsReadForm = notificationItem?.querySelector("[data-notifications-read-form]");
    const knownNotificationIds = new Set(
        [...(notificationList?.querySelectorAll("[data-notification-id]") || [])]
            .map((notification) => notification.dataset.notificationId)
    );
    let notificationSummaryRequest = null;
    let notificationToastTimer = null;
    let notificationState = null;

    const notificationToastRegion = document.createElement("div");
    notificationToastRegion.className = "notification-live-toast-region";
    notificationToastRegion.setAttribute("aria-live", "polite");
    notificationToastRegion.setAttribute("aria-atomic", "true");
    document.body.append(notificationToastRegion);

    const showNotificationToast = (newNotifications, allUrl) => {
        if (!newNotifications.length) return;
        window.clearTimeout(notificationToastTimer);
        const toast = document.createElement("button");
        toast.type = "button";
        toast.className = "notification-live-toast";
        const heading = document.createElement("strong");
        const detail = document.createElement("span");
        if (newNotifications.length === 1) {
            heading.textContent = "New notification received";
            detail.textContent = newNotifications[0].title;
        } else {
            heading.textContent = `${newNotifications.length} new notifications received`;
            detail.textContent = "Open notifications to view them.";
        }
        toast.addEventListener("click", () => {
            window.location.assign(allUrl);
        });
        toast.append(heading, detail);
        notificationToastRegion.replaceChildren(toast);
        requestAnimationFrame(() => toast.classList.add("is-visible"));
        notificationToastTimer = window.setTimeout(() => {
            toast.classList.remove("is-visible");
            window.setTimeout(() => toast.remove(), 180);
        }, 5000);
    };

    const renderNotificationSummary = (summary, announce = false) => {
        if (!notificationItem || !notificationToggle || !notificationList) return;
        const nextNotificationState = `${summary.unread_count}:${
            summary.notifications.map((notification) => (
                `${notification.id}:${notification.is_read ? "1" : "0"}`
            )).join(",")
        }`;
        const stateChanged = notificationState !== null
            && nextNotificationState !== notificationState;
        notificationState = nextNotificationState;
        const newNotifications = summary.notifications.filter(
            (notification) => !knownNotificationIds.has(notification.id)
        );
        summary.notifications.forEach((notification) => {
            knownNotificationIds.add(notification.id);
        });

        notificationItem.dataset.unreadCount = String(summary.unread_count);
        notificationToggle.setAttribute(
            "aria-label",
            summary.unread_count
                ? `Notifications, ${summary.unread_count} unread`
                : "Notifications"
        );
        let count = notificationToggle.querySelector(".notification-count");
        if (summary.unread_count) {
            if (!count) {
                count = document.createElement("span");
                count.className = "notification-count";
                notificationToggle.append(count);
            }
            count.textContent = String(summary.unread_count);
        } else {
            count?.remove();
        }

        notificationList.replaceChildren();
        if (summary.notifications.length) {
            summary.notifications.forEach((notification) => {
                const link = document.createElement("a");
                link.className = `notification-preview${notification.is_read ? "" : " is-unread"}`;
                link.href = notification.open_url;
                link.dataset.notificationId = notification.id;
                const title = document.createElement("strong");
                title.textContent = notification.title;
                const message = document.createElement("span");
                message.textContent = notification.message;
                const time = document.createElement("time");
                time.dateTime = notification.created_at;
                time.textContent = notification.age;
                link.append(title, message, time);
                notificationList.append(link);
            });
        } else {
            const empty = document.createElement("p");
            empty.className = "utility-empty-state";
            empty.textContent = "You have no notifications.";
            notificationList.append(empty);
        }

        if (notificationsReadForm) {
            notificationsReadForm.hidden = summary.unread_count === 0;
            const button = notificationsReadForm.querySelector("button[type='submit']");
            if (button) {
                button.disabled = false;
                button.textContent = "Mark all as read";
            }
        }
        if (announce) showNotificationToast(newNotifications, summary.all_url);
        if (stateChanged) {
            document.dispatchEvent(new CustomEvent("notifications:changed"));
        }
    };

    const refreshNotificationSummary = (announce = false) => {
        if (!notificationItem || notificationSummaryRequest) return notificationSummaryRequest;
        notificationSummaryRequest = fetch(notificationItem.dataset.summaryUrl, {
            credentials: "same-origin",
            headers: {"Accept": "application/json"},
            cache: "no-store",
        })
            .then((response) => {
                if (!response.ok) throw new Error("Unable to refresh notifications.");
                return response.json();
            })
            .then((summary) => renderNotificationSummary(summary, announce))
            .catch(() => {})
            .finally(() => {
                notificationSummaryRequest = null;
            });
        return notificationSummaryRequest;
    };
    const closeSubmenus = () => {
        submenuToggles.forEach((submenuToggle) => {
            submenuToggle.setAttribute("aria-expanded", "false");
            submenuToggle.closest(".site-nav-item")?.classList.remove("is-open");
        });
    };

    const closeMenu = (restoreFocus = false) => {
        menu.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
        closeSubmenus();
        if (restoreFocus) toggle.focus();
    };

    submenuToggles.forEach((submenuToggle) => {
        submenuToggle.addEventListener("click", (event) => {
            event.stopPropagation();
            const desktopHoverNavigation = window.matchMedia("(hover: hover) and (pointer: fine)").matches
                && getComputedStyle(toggle).display === "none";
            const utilityItem = submenuToggle.closest(".site-utility-item");
            if (desktopHoverNavigation && !utilityItem && event.detail !== 0) {
                submenuToggle.blur();
                return;
            }
            const item = submenuToggle.closest(".site-nav-item");
            const opening = submenuToggle.getAttribute("aria-expanded") !== "true";
            headerControls.querySelectorAll(".site-nav-item.is-open").forEach((sibling) => {
                const isAncestorOfItem = item && sibling.contains(item);
                if (sibling !== item && !isAncestorOfItem) {
                    sibling.classList.remove("is-open");
                    sibling.querySelector(":scope > .site-nav-entry [data-nav-submenu-toggle]")?.setAttribute("aria-expanded", "false");
                }
            });
            if (utilityItem && opening) {
                menu.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            }
            item?.classList.toggle("is-open", opening);
            submenuToggle.setAttribute("aria-expanded", String(opening));
        });
    });

    notificationsReadForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submitButton = notificationsReadForm.querySelector("button[type='submit']");
        submitButton.disabled = true;
        try {
            const response = await fetch(notificationsReadForm.action, {
                method: "POST",
                body: new FormData(notificationsReadForm),
                credentials: "same-origin",
                headers: {"X-Requested-With": "XMLHttpRequest"},
            });
            if (!response.ok) throw new Error("Unable to mark notifications as read.");
            await response.json();
            headerControls.querySelectorAll(".notification-preview.is-unread").forEach((notification) => {
                notification.classList.remove("is-unread");
            });
            document.querySelectorAll(".notification-history-item.is-unread").forEach((notification) => {
                notification.classList.remove("is-unread");
            });
            headerControls.querySelector(".notification-count")?.remove();
            notificationToggle?.setAttribute("aria-label", "Notifications");
            notificationsReadForm.hidden = true;
            await refreshNotificationSummary(false);
        } catch (error) {
            submitButton.disabled = false;
            submitButton.textContent = "Try again";
        }
    });

    if (notificationItem) {
        refreshNotificationSummary(false);
        if ("EventSource" in window) {
            const stream = new EventSource(notificationItem.dataset.streamUrl);
            stream.addEventListener("notifications-changed", () => {
                refreshNotificationSummary(true);
            });
        }
        window.setInterval(() => {
            if (document.visibilityState === "visible") {
                refreshNotificationSummary(true);
            }
        }, 60000);
        document.addEventListener("visibilitychange", () => {
            if (document.visibilityState === "visible") {
                refreshNotificationSummary(true);
            }
        });
    }

    toggle.addEventListener("click", () => {
        const opening = !menu.classList.contains("is-open");
        closeSubmenus();
        menu.classList.toggle("is-open", opening);
        toggle.setAttribute("aria-expanded", String(opening));
    });
    document.addEventListener("click", (event) => {
        if (!headerControls.contains(event.target)) {
            closeMenu();
            closeSubmenus();
        }
    });
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.classList.contains("is-open")) {
            closeMenu(true);
        }
    });
    window.matchMedia("(min-width: 34.01rem)").addEventListener("change", (event) => {
        if (event.matches) closeMenu();
    });
})();
