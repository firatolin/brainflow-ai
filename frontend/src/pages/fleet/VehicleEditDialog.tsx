import { useEffect } from "react";
import { useForm } from "react-hook-form";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Vehicle, VehicleUpdateInput } from "@/api/endpoints";

type Props = {
  vehicle: Vehicle | null;
  onOpenChange: (open: boolean) => void;
  submitting: boolean;
  onSubmit: (id: number, input: VehicleUpdateInput) => void;
};

export function VehicleEditDialog({ vehicle, onOpenChange, submitting, onSubmit }: Props) {
  const { register, handleSubmit, reset, setValue, watch } = useForm<VehicleUpdateInput>({
    defaultValues: {},
  });
  const statusValue = watch("status");

  useEffect(() => {
    if (vehicle) {
      reset({
        status: vehicle.status,
        capacity: vehicle.capacity,
        location_zone: vehicle.location_zone,
        available: vehicle.available,
        cost_per_km: vehicle.cost_per_km,
      });
    }
  }, [vehicle, reset]);

  if (!vehicle) return null;

  const submit = (v: VehicleUpdateInput) => {
    const payload: VehicleUpdateInput = {
      ...v,
      available: v.status ? v.status === "available" : vehicle.available,
    };
    onSubmit(vehicle.id, payload);
  };

  return (
    <Dialog open={!!vehicle} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit vehicle {vehicle.code}</DialogTitle>
          <DialogDescription>Changes are audited.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(submit)} className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Status</Label>
            <Select value={statusValue ?? vehicle.status} onValueChange={(v) => setValue("status", v as VehicleUpdateInput["status"])}>
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
            <Label htmlFor="capacity">Capacity</Label>
            <Input id="capacity" type="number" {...register("capacity")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="location_zone">Zone</Label>
            <Input id="location_zone" {...register("location_zone")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="cost_per_km">Cost per km</Label>
            <Input id="cost_per_km" type="number" step="0.01" {...register("cost_per_km")} />
          </div>
          <DialogFooter className="col-span-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>Cancel</Button>
            <Button type="submit" disabled={submitting}>{submitting ? "Saving…" : "Save changes"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
