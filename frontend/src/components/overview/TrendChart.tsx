import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type Point = { date: string; created: number; delivered: number };

export function TrendChart({ data }: { data: Point[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -16 }}>
          <CartesianGrid stroke="#f1f5f9" vertical={false} />
          <XAxis
            dataKey="date"
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "#64748b" }}
            width={32}
            allowDecimals={false}
          />
          <Tooltip
            cursor={{ stroke: "#e2e8f0" }}
            contentStyle={{
              borderRadius: 8,
              border: "1px solid #e2e8f0",
              fontSize: 12,
              padding: "6px 10px",
            }}
          />
          <Area
            type="monotone"
            dataKey="created"
            name="Created"
            stroke="#2563eb"
            strokeWidth={1.5}
            fill="#2563eb"
            fillOpacity={0.08}
          />
          <Area
            type="monotone"
            dataKey="delivered"
            name="Delivered"
            stroke="#10b981"
            strokeWidth={1.5}
            fill="#10b981"
            fillOpacity={0.08}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
