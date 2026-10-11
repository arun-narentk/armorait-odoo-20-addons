/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, proxy, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RnJewelleryManufacturingDashboard extends Component {
    static template = "rn_jewellery_core.ManufacturingDashboard";

    setup() {
        this.orm = useService("orm");
        this.state = proxy({ loading: true, data: {} });
        onWillStart(async () => { await this.refresh(); });
    }

    formatNumber(value) {
        return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 3 });
    }

    async refresh() {
        this.state.loading = true;
        const data = await this.orm.call("rn.jewellery.dashboard.service", "get_manufacturing_dashboard", []);
        Object.assign(this.state, { loading: false, data: data || {} });
    }
}

registry.category("actions").add("rn_jewellery_core.manufacturing_dashboard", RnJewelleryManufacturingDashboard);
