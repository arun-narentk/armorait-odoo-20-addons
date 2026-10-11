/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useLayoutEffect } from "@web/owl2/utils";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useProps } from "@odoo/owl";

export class RnSmartSearchTrackerWidget extends Component {
    static template = "rn_smart_search.Tracker";
    props = useProps({ ...standardWidgetProps });

    setup() {
        this.orm = useService("orm");
        onWillStart(() => this.trackView());
        useLayoutEffect(
            () => {
                this.trackView();
            },
            () => [this.props.record.resId]
        );
    }

    async trackView() {
        const resId = this.props.record.resId;
        const resModel = this.props.record.resModel;
        if (!resId || !resModel) {
            return;
        }
        try {
            await this.orm.call(resModel, "smart_search_track_view", [[resId]]);
        } catch (_error) {
            // Tracking should never block form rendering.
        }
    }
}

export const rnSmartSearchTracker = {
    component: RnSmartSearchTrackerWidget,
};

registry.category("view_widgets").add("rn_smart_search_tracker", rnSmartSearchTracker);
