/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, proxy, usePlugin } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class RnDocumentIdpDashboard extends Component {
    static template = "rn_document_idp.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = usePlugin(ActionPlugin);
        this.state = proxy({
            loading: true,
            data: {},
            query: "",
            searchResults: [],
        });
        onWillStart(async () => {
            await this.reload();
        });
    }

    async reload() {
        this.state.loading = true;
        this.state.data = await this.orm.call(
            "rn.document.idp.dashboard.service",
            "get_dashboard_data",
            []
        );
        this.state.loading = false;
    }

    async runSearch() {
        if (!this.state.query.trim()) {
            this.state.searchResults = [];
            return;
        }
        this.state.searchResults = await this.orm.call(
            "rn.document.idp.search.service",
            "search_documents",
            [],
            { query: this.state.query, limit: 10 }
        );
    }

    openDocument(docId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "rn.document.idp.document",
            res_id: docId,
            view_mode: "form",
        });
    }
}

registry.category("actions").add("rn_document_idp.dashboard", RnDocumentIdpDashboard);
