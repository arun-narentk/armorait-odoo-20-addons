/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, proxy, onWillStart, useProps } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { useService } from "@web/core/utils/hooks";

export class RnFleetDashboard extends Component {
    static template = "rn_fleet_gps.Dashboard";
    props = useProps({ ...standardActionServiceProps });

    setup() {
        this.orm = useService("orm");
        this.state = proxy({
            loading: true,
            cards: {},
            mapPoints: [],
            edition: "base",
            updatedAt: "",
        });
        onWillStart(async () => {
            await this.refresh();
        });
    }

    get vehicleId() {
        return this.props.action?.params?.vehicle_id || false;
    }

    formatNumber(value) {
        return Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
    }

    async refresh() {
        this.state.loading = true;
        const data = await this.orm.call(
            "rn.fleet.dashboard.service",
            "get_dashboard_data",
            [false, this.vehicleId || false]
        );
        Object.assign(this.state, {
            loading: false,
            cards: data.cards || {},
            mapPoints: data.map_points || [],
            edition: data.edition || "base",
            updatedAt: data.updated_at || "",
        });
    }
}

registry.category("actions").add("rn_fleet_gps.dashboard", RnFleetDashboard);
