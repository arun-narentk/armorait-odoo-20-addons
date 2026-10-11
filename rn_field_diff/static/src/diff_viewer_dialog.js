/** @odoo-module **/

import { Component, onWillStart, proxy, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { fetchFieldDiffs, fetchFieldDiffSummary } from "./field_diff_service";

export class DiffViewerDialog extends Component {
    static template = "rn_field_diff.DiffViewerDialog";
    static components = { Dialog };
    props = useProps({
        close: t.function(),
        model: t.string(),
        resId: t.number(),
        title: t.string().optional(),
    });

    setup() {
        this.state = proxy({ diffs: [], summary: {}, loading: true });
        onWillStart(async () => {
            const [diffs, summary] = await Promise.all([
                fetchFieldDiffs(this.props.model, this.props.resId),
                fetchFieldDiffSummary(this.props.model, this.props.resId),
            ]);
            this.state.diffs = diffs;
            this.state.summary = summary;
            this.state.loading = false;
        });
    }
}
