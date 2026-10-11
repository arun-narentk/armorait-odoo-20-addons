/** @odoo-module **/

import { NotificationPlugin } from "@web/core/notifications/notification_plugin";
import { registry } from "@web/core/registry";
import { useLayoutEffect } from "@web/owl2/utils";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, proxy, usePlugin, useProps } from "@odoo/owl";
import { clearBookmarkStateCache } from "./bookmark_helpers";

export class RnBookmarkToggleWidget extends Component {
    static template = "rn_bookmarks.BookmarkToggle";
    props = useProps({ ...standardWidgetProps });

    setup() {
        this.orm = useService("orm");
        this.notification = usePlugin(NotificationPlugin);
        this.state = proxy({
            bookmarked: false,
            bookmarkId: false,
            loading: false,
        });
        onWillStart(() => this.refresh());
        useLayoutEffect(
            () => {
                if (this.resId) {
                    this.refresh();
                }
            },
            () => [this.props.record.resId]
        );
    }

    get resModel() {
        return this.props.record.resModel;
    }

    get resId() {
        return this.props.record.resId;
    }

    async refresh() {
        if (!this.resId) {
            this.state.bookmarked = false;
            this.state.bookmarkId = false;
            return;
        }
        const data = await this.orm.call(
            "rn.bookmark.service",
            "get_current_context_bookmark_state",
            [this.resModel, this.resId]
        );
        this.state.bookmarked = data.bookmarked;
        this.state.bookmarkId = data.bookmark_id;
    }

    async onToggle() {
        if (!this.resId || this.state.loading) {
            return;
        }
        this.state.loading = true;
        const wasBookmarked = this.state.bookmarked;
        try {
            await this.orm.call(this.resModel, "action_toggle_rn_bookmark", [[this.resId]]);
            clearBookmarkStateCache();
            await this.refresh();
            await this.props.record.load();
            this.notification.add(
                !wasBookmarked ? "Bookmark saved." : "Bookmark removed.",
                { type: "success" }
            );
        } catch (error) {
            this.notification.add("Could not update bookmark.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }
}

export const rnBookmarkToggle = {
    component: RnBookmarkToggleWidget,
};

registry.category("view_widgets").add("rn_bookmark_toggle", rnBookmarkToggle);
