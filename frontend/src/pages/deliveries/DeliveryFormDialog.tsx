import { useEffect } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { DeliveryCreateInput, Vehicle } from "@/api/endpoints";

const schema = z.object({
  tracking_number: z.string().min(3).max(40),
  customer_ref: z.string().min(1).max(120),
  origin: z.string().min(1).max(200),
  destination: z.string().min(1).max(200),
  scheduled_dispatch: z.string().min(1),
  promised_deadline: z.string().min(1),
  priority: z.enum(["low", "normal", "high", "urgent"]),
  distance_km: z.coerce.number().min(0),
  cost_estimate: z.coerce.number().min(0),
  weather_exposure: z.coerce.number().min(0).max(1),
  vehicle_id: z.coerce.number().int().positive().optional().nullable(),
});

type FormValues = z.infer<typeof schema>;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  submitting: boolean;
  onSubmit: (input: DeliveryCreateInput) => void;
  vehicles: Vehicle[];
};

function defaultDeadline(): string {
  const d = new Date();
  d.setHours(d.getHours() + 4);
  return d.toISOString().slice(0, 16);
}

function defaultDispatch(): string {
  return new Date().toISOString().slice(0, 16);
}

export function DeliveryFormDialog({ open, onOpenChange, submitting, onSubmit, vehicles }: Props) {
  const { register, handleSubmit, reset, formState: { errors }, setValue, watch } = useForm<FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: {
      priority: "normal",
      distance_km: 10,
      cost_estimate: 20,
      weather_exposure: 0.1,
      vehicle_id: null,
      origin: "Main Warehouse",
      scheduled_dispatch: defaultDispatch(),
      promised_deadline: defaultDeadline(),
    },
  });

  const vehicleValue = watch("vehicle_id");

  useEffect(() => {
    if (!open) {
      reset();
    }
  }, [open, reset]);

  const submit = (v: FormValues) => {
    const payload: DeliveryCreateInput = {
      tracking_number: v.tracking_number,
      customer_ref: v.customer_ref,
      origin: v.origin,
      destination: v.destination,
      scheduled_dispatch: new Date(v.scheduled_dispatch).toISOString(),
      promised_deadline: new Date(v.promised_deadline).toISOString(),
      priority: v.priority,
      distance_km: v.distance_km,
      cost_estimate: v.cost_estimate,
      weather_exposure: v.weather_exposure,
      vehicle_id: v.vehicle_id ?? null,
    };
    onSubmit(payload);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>New delivery</DialogTitle>
          <DialogDescription>Create a delivery. All data is demonstration-only.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="space-y-1.5 md:col-span-2">
            <Label htmlFor="tracking_number">Tracking number</Label>
            <Input id="tracking_number" {...register("tracking_number")} />
            {errors.tracking_number && <p className="text-xs text-red-600">{errors.tracking_number.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="customer_ref">Customer reference</Label>
            <Input id="customer_ref" {...register("customer_ref")} />
            {errors.customer_ref && <p className="text-xs text-red-600">{errors.customer_ref.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Priority</Label>
            <Select
              defaultValue="normal"
              onValueChange={(v) => setValue("priority", v as FormValues["priority"])}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="origin">Origin</Label>
            <Input id="origin" {...register("origin")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="destination">Destination</Label>
            <Input id="destination" {...register("destination")} />
            {errors.destination && <p className="text-xs text-red-600">{errors.destination.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="scheduled_dispatch">Scheduled dispatch</Label>
            <Input id="scheduled_dispatch" type="datetime-local" {...register("scheduled_dispatch")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="promised_deadline">Promised deadline</Label>
            <Input id="promised_deadline" type="datetime-local" {...register("promised_deadline")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="distance_km">Distance (km)</Label>
            <Input id="distance_km" type="number" step="0.1" {...register("distance_km")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cost_estimate">Cost estimate</Label>
            <Input id="cost_estimate" type="number" step="0.01" {...register("cost_estimate")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="weather_exposure">Weather exposure (0–1)</Label>
            <Input id="weather_exposure" type="number" step="0.05" min={0} max={1} {...register("weather_exposure")} />
          </div>
          <div className="space-y-1.5">
            <Label>Assign to vehicle</Label>
            <Select
              value={vehicleValue ? String(vehicleValue) : "none"}
              onValueChange={(v) => setValue("vehicle_id", v === "none" ? null : Number(v))}
            >
              <SelectTrigger><SelectValue placeholder="Leave unassigned" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Leave unassigned</SelectItem>
                {vehicles.filter((v) => v.available).map((v) => (
                  <SelectItem key={v.id} value={String(v.id)}>{v.code} ({v.vehicle_type}, cap {v.capacity})</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter className="md:col-span-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creating…" : "Create delivery"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
