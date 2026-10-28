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
import type { VehicleCreateInput } from "@/api/endpoints";

const schema = z.object({
  code: z.string().min(1).max(40),
  vehicle_type: z.enum(["van", "truck", "motorbike", "car"]),
  capacity: z.coerce.number().int().min(1).max(500),
  status: z.enum(["available", "on_route", "maintenance", "out_of_service"]),
  location_zone: z.string().min(1).max(120),
  available: z.boolean(),
  cost_per_km: z.coerce.number().min(0),
});
type FormValues = z.infer<typeof schema>;

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  submitting: boolean;
  onSubmit: (input: VehicleCreateInput) => void;
};

export function VehicleFormDialog({ open, onOpenChange, submitting, onSubmit }: Props) {
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema) as Resolver<FormValues>,
    defaultValues: {
      vehicle_type: "van",
      capacity: 4,
      status: "available",
      location_zone: "central",
      available: true,
      cost_per_km: 1,
    },
  });
  const statusValue = watch("status");

  useEffect(() => { if (!open) reset(); }, [open, reset]);

  const submit = (v: FormValues) => {
    const payload: VehicleCreateInput = {
      ...v,
      available: v.status === "available",
    };
    onSubmit(payload);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>New vehicle</DialogTitle>
          <DialogDescription>Add a vehicle to the demonstration fleet.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5 col-span-2">
            <Label htmlFor="code">Code</Label>
            <Input id="code" {...register("code")} />
            {errors.code && <p className="text-xs text-red-600">{errors.code.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select defaultValue="van" onValueChange={(v) => setValue("vehicle_type", v as FormValues["vehicle_type"])}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="van">Van</SelectItem>
                <SelectItem value="truck">Truck</SelectItem>
                <SelectItem value="motorbike">Motorbike</SelectItem>
                <SelectItem value="car">Car</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="capacity">Capacity</Label>
            <Input id="capacity" type="number" {...register("capacity")} />
          </div>
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select
              value={statusValue}
              onValueChange={(v) => setValue("status", v as FormValues["status"])}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="available">Available</SelectItem>
                <SelectItem value="on_route">On route</SelectItem>
                <SelectItem value="maintenance">Maintenance</SelectItem>
                <SelectItem value="out_of_service">Out of service</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="location_zone">Zone</Label>
            <Input id="location_zone" {...register("location_zone")} />
          </div>
          <div className="space-y-1.5 col-span-2">
            <Label htmlFor="cost_per_km">Cost per km</Label>
            <Input id="cost_per_km" type="number" step="0.01" {...register("cost_per_km")} />
          </div>
          <DialogFooter className="col-span-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Creating…" : "Create vehicle"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
