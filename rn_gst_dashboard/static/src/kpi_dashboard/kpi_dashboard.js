import { _t } from "@web/core/l10n/translation";
import { getCurrency } from "@web/core/currency";
import { registry } from "@web/core/registry";
import { useChart } from "@web/core/utils/chart_hook";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

import { Component, onWillStart, proxy, t, useProps } from "@odoo/owl";

const { DateTime } = luxon;

const COLORS = {
    blue: "#1A73E8",
    cyan: "#22B8F0",
    amber: "#F4A62A",
    green: "#16A34A",
    red: "#DC2626",
    slate: "#64748B",
    violet: "#7C3AED",
};
const TAX_HEADS = [
    ["igst", "IGST", COLORS.blue],
    ["cgst", "CGST", COLORS.cyan],
    ["sgst", "SGST/UTGST", COLORS.amber],
    ["cess", "Cess", COLORS.violet],
];

export class GstKpiChart extends Component {
    static template = "rn_gst_dashboard.GstKpiChart";
    props = useProps({
        config: t.object(),
    });

    setup() {
        this.chart = useChart(() => this.props.config);
    }
}

export class GstKpiDashboard extends Component {
    static template = "rn_gst_dashboard.GstKpiDashboard";
    static components = { GstKpiChart };
    props = useProps(standardActionServiceProps);

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = proxy({ data: null, loading: true });
        this.colors = COLORS;
        this.lastRequestId = 0;
        onWillStart(() => this.load());
    }

    async load(financialYear = null, returnPeriod = null) {
        // Only the latest request may update the screen when filters change quickly.
        const requestId = ++this.lastRequestId;
        this.state.loading = true;
        const data = await this.orm.call("rn.gst.dashboard", "get_kpi_dashboard_data", [], {
            financial_year: financialYear,
            return_period: returnPeriod,
        });
        if (requestId === this.lastRequestId) {
            this.state.data = data;
            this.state.loading = false;
        }
    }

    onFinancialYearChange(ev) {
        this.load(ev.target.value, this.state.data.filters.return_period);
    }

    onPeriodChange(ev) {
        this.load(this.state.data.filters.financial_year, ev.target.value);
    }

    // Formatting ----------------------------------------------------------

    formatAmount(value) {
        return formatMonetary(value || 0, { currencyId: this.state.data.company.currency_id });
    }

    formatCompact(value) {
        const amount = value || 0;
        const abs = Math.abs(amount);
        const currency = getCurrency(this.state.data.company.currency_id);
        const symbol = currency ? currency.symbol : "";
        if (abs >= 1e7) {
            return `${symbol} ${(amount / 1e7).toFixed(2)} Cr`;
        }
        if (abs >= 1e5) {
            return `${symbol} ${(amount / 1e5).toFixed(2)} L`;
        }
        return formatMonetary(amount, {
            currencyId: this.state.data.company.currency_id,
            digits: [16, 0],
        });
    }

    periodLabel() {
        const date = DateTime.fromISO(this.state.data.period.date_from);
        return date.toFormat("LLLL yyyy");
    }

    monthLabel(month) {
        return DateTime.fromObject({ month: parseInt(month), day: 1 }).toFormat("LLLL");
    }

    change(key) {
        const now = this.state.data.kpis[key] || 0;
        const before = this.state.data.previous_kpis[key] || 0;
        if (!before) {
            return null;
        }
        const pct = ((now - before) / Math.abs(before)) * 100;
        return { pct: Math.abs(pct).toFixed(1), up: pct >= 0 };
    }

    kpiCards() {
        const k = this.state.data.kpis;
        return [
            {
                key: "output_tax",
                label: _t("Output GST"),
                hint: _t("Tax on sales and credit notes"),
                value: k.output_tax,
                icon: "arrow_upward",
                tone: "blue",
                open: () => this.openMoves(["out_invoice", "out_refund"], _t("Sales")),
            },
            {
                key: "input_tax",
                label: _t("Input GST (ITC)"),
                hint: _t("Tax on vendor bills"),
                value: k.input_tax,
                icon: "arrow_downward",
                tone: "cyan",
                open: () => this.openMoves(["in_invoice", "in_refund"], _t("Purchases")),
            },
            {
                key: "net_payable",
                label: k.net_payable >= 0 ? _t("Net GST payable") : _t("Excess ITC"),
                hint: _t("Output GST minus input GST, before set-off rules"),
                value: Math.abs(k.net_payable),
                icon: "account_balance",
                tone: k.net_payable >= 0 ? "amber" : "green",
            },
            {
                key: "sales_taxable",
                label: _t("Taxable sales"),
                hint: _t("Invoices minus credit notes, before tax"),
                value: k.sales_taxable,
                icon: "show_chart",
                tone: "violet",
                open: () => this.openMoves(["out_invoice", "out_refund"], _t("Sales")),
            },
        ];
    }

    countCards() {
        const k = this.state.data.kpis;
        return [
            { label: _t("Invoices"), value: k.invoice_count, icon: "description", types: ["out_invoice"] },
            { label: _t("Credit notes"), value: k.credit_note_count, icon: "undo", types: ["out_refund"] },
            { label: _t("Vendor bills"), value: k.bill_count, icon: "shopping_cart", types: ["in_invoice"] },
            { label: _t("Purchases (taxable)"), value: this.formatCompact(k.purchase_taxable), icon: "local_shipping", types: ["in_invoice", "in_refund"] },
        ];
    }

    healthColor() {
        const score = this.state.data.health.score;
        if (score >= 80) {
            return COLORS.green;
        }
        if (score >= 50) {
            return COLORS.amber;
        }
        return COLORS.red;
    }

    healthRingStyle() {
        const score = this.state.data.health.score || 0;
        return `background: conic-gradient(${this.healthColor()} ${score * 3.6}deg, #E2E8F0 0deg);`;
    }

    deadlineTone(deadline) {
        if (deadline.done) {
            return "success";
        }
        if (deadline.days_left < 0) {
            return "danger";
        }
        if (deadline.days_left <= 5) {
            return "warning";
        }
        return "info";
    }

    deadlineText(deadline) {
        if (deadline.done) {
            return _t("Done");
        }
        if (deadline.days_left < 0) {
            return _t("%s days overdue", -deadline.days_left);
        }
        if (deadline.days_left === 0) {
            return _t("Due today");
        }
        return _t("%s days left", deadline.days_left);
    }

    formatDate(value) {
        return DateTime.fromISO(value).toFormat("dd LLL yyyy");
    }

    reconBars() {
        const r = this.state.data.reconciliation_2b.kpis;
        const rows = [
            [_t("Matched"), r.exact_matches, COLORS.green],
            [_t("Mismatch"), r.mismatches, COLORS.red],
            [_t("Missing in Odoo"), r.missing_in_books, COLORS.amber],
            [_t("Missing in 2B"), r.missing_in_2b, COLORS.slate],
        ];
        const total = rows.reduce((sum, row) => sum + (row[1] || 0), 0);
        return rows.map(([label, value, color]) => ({
            label,
            value: value || 0,
            color,
            pct: total ? Math.round(((value || 0) * 100) / total) : 0,
        }));
    }

    filingSteps() {
        const f = this.state.data.filing.kpis;
        return [
            [_t("Pending"), f.pending_filings],
            [_t("Validated"), f.validated_filings],
            [_t("Generated"), f.generated_filings],
            [_t("Submitted"), f.submitted_filings],
            [_t("Filed"), f.filed_filings],
        ].map(([label, value]) => ({ label, value: value || 0 }));
    }

    // Charts ----------------------------------------------------------------

    trendConfig() {
        const trend = this.state.data.trend;
        const labels = trend.months.map((m) => DateTime.fromISO(m).toFormat("LLL yy"));
        return {
            type: "bar",
            data: {
                labels,
                datasets: [
                    {
                        label: _t("Output GST"),
                        data: trend.output_tax,
                        backgroundColor: COLORS.blue,
                        borderRadius: 6,
                        maxBarThickness: 26,
                    },
                    {
                        label: _t("Input GST"),
                        data: trend.input_tax,
                        backgroundColor: COLORS.cyan,
                        borderRadius: 6,
                        maxBarThickness: 26,
                    },
                    {
                        type: "line",
                        label: _t("Net payable"),
                        data: trend.output_tax.map((v, i) => v - trend.input_tax[i]),
                        borderColor: COLORS.amber,
                        backgroundColor: COLORS.amber,
                        tension: 0.35,
                        pointRadius: 4,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${this.formatAmount(ctx.parsed.y)}`,
                        },
                    },
                },
                scales: {
                    x: { grid: { display: false } },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(100, 116, 139, 0.12)" },
                        ticks: { callback: (v) => this.formatCompact(v) },
                    },
                },
            },
        };
    }

    splitConfig() {
        const split = this.state.data.output_split;
        return {
            type: "doughnut",
            data: {
                labels: TAX_HEADS.map((h) => h[1]),
                datasets: [
                    {
                        data: TAX_HEADS.map((h) => split[h[0]] || 0),
                        backgroundColor: TAX_HEADS.map((h) => h[2]),
                        borderWidth: 0,
                        hoverOffset: 6,
                    },
                ],
            },
            options: {
                maintainAspectRatio: false,
                cutout: "68%",
                plugins: {
                    legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8 } },
                    tooltip: {
                        callbacks: { label: (ctx) => `${ctx.label}: ${this.formatAmount(ctx.parsed)}` },
                    },
                },
            },
        };
    }

    hasTrend() {
        const trend = this.state.data.trend;
        return [...trend.output_tax, ...trend.input_tax].some((v) => v);
    }

    hasOutputSplit() {
        const split = this.state.data.output_split;
        return TAX_HEADS.some((h) => split[h[0]]);
    }

    taxHeadRows() {
        const out = this.state.data.output_split;
        const inp = this.state.data.input_split;
        return TAX_HEADS.map(([key, label, color]) => ({
            key,
            label,
            color,
            output: out[key] || 0,
            input: inp[key] || 0,
        }));
    }

    // Navigation ------------------------------------------------------------

    openMoves(moveTypes, name) {
        const period = this.state.data.period;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `${name} - ${this.periodLabel()}`,
            res_model: "account.move",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: [
                ["move_type", "in", moveTypes],
                ["state", "=", "posted"],
                ["invoice_date", ">=", period.date_from],
                ["invoice_date", "<=", period.date_to],
            ],
        });
    }

    openPartner(partnerId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
        });
    }

    openRecord(resModel, resId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
        });
    }

    openAction(xmlId) {
        this.actionService.doAction(xmlId);
    }
}

registry.category("actions").add("rn_gst_kpi_dashboard", GstKpiDashboard);
