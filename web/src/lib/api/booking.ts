/** Appointments (module 8): the booking page, the client's appointments, the agenda. */
import { api, unwrap, type Schemas } from "./client";

export type BookingPage = Schemas["BookingPage"];
export type BookableService = Schemas["BookableService"];
export type StaffBrief = Schemas["StaffBrief"];
export type Slot = Schemas["Slot"];
export type SlotDay = Schemas["SlotDay"];
export type Appointment = Schemas["Appointment"];
export type AppointmentStatus = Appointment["status"];
export type Booked = Schemas["Booked"];
export type WaitlistEntry = Schemas["WaitlistEntry"];
export type Group = Schemas["Group"];
export type Agenda = Schemas["Agenda"];
export type Staff = Schemas["Staff"];
export type TimeOff = Schemas["TimeOff"];
export type AgendaSettings = Schemas["AgendaSettings"];
export type AppointmentDetail = Schemas["AppointmentDetail"];
export type ClientRecord = Schemas["ClientRecord"];
export type ClientRecordDetail = Schemas["ClientRecordDetail"];
export type HoursRow = Schemas["HoursRow"];

const slug = (value: string) => ({ params: { path: { slug: value } } });
const mine = (id: string) => ({ params: { path: { appointment_id: id } } });
const guest = (token: string) => ({ params: { path: { token } } });

// --- Public --------------------------------------------------------------------------------------

export const getBookingPage = (proSlug: string) =>
  unwrap(api.GET("/api/v1/pros/{slug}/booking", slug(proSlug)));

export const getSlots = (
  proSlug: string,
  query: { service: string; day?: string; days?: number; staff?: string; options?: string },
) =>
  unwrap(
    api.GET("/api/v1/pros/{slug}/booking/slots", {
      params: { path: { slug: proSlug }, query },
    }),
  );

export const book = (proSlug: string, body: Schemas["BookInputRequest"]) =>
  unwrap(api.POST("/api/v1/pros/{slug}/booking", { ...slug(proSlug), body }));

export const joinWaitlist = (proSlug: string, body: Schemas["WaitlistInputRequest"]) =>
  unwrap(api.POST("/api/v1/pros/{slug}/booking/waitlist", { ...slug(proSlug), body }));

export const createGroup = (proSlug: string, body: Schemas["GroupInputRequest"]) =>
  unwrap(api.POST("/api/v1/pros/{slug}/booking/groups", { ...slug(proSlug), body }));

export const getGroup = (token: string) =>
  unwrap(api.GET("/api/v1/booking/groups/{token}", guest(token)));

export const payGroupShare = (token: string, placeId?: string) =>
  unwrap(
    api.POST("/api/v1/booking/groups/{token}/share", {
      ...guest(token),
      body: { place_id: placeId ?? null },
    }),
  );

// --- The client, or the guest with her link ------------------------------------------------------

export const getMyAppointments = () => unwrap(api.GET("/api/v1/booking/appointments"));

export const getMyAppointment = (id: string) =>
  unwrap(api.GET("/api/v1/booking/appointments/{appointment_id}", mine(id)));

export const getGuestAppointment = (token: string) =>
  unwrap(api.GET("/api/v1/booking/manage/{token}", guest(token)));

/** Who acts: the signed-in client (by id) or the guest (by her secret link). */
export type Holder = { id: string } | { token: string };

export const cancelAppointment = (holder: Holder) =>
  "id" in holder
    ? unwrap(
        api.POST("/api/v1/booking/appointments/{appointment_id}/cancel", {
          ...mine(holder.id),
          body: {},
        }),
      )
    : unwrap(
        api.POST("/api/v1/booking/manage/{token}/cancel", { ...guest(holder.token), body: {} }),
      );

export const answerProposal = (holder: Holder, accept: boolean) =>
  "id" in holder
    ? unwrap(
        api.POST("/api/v1/booking/appointments/{appointment_id}/answer", {
          ...mine(holder.id),
          body: { accept },
        }),
      )
    : unwrap(
        api.POST("/api/v1/booking/manage/{token}/answer", {
          ...guest(holder.token),
          body: { accept },
        }),
      );

export const acceptOffer = (holder: Holder) =>
  "id" in holder
    ? unwrap(api.POST("/api/v1/booking/appointments/{appointment_id}/accept", mine(holder.id)))
    : unwrap(api.POST("/api/v1/booking/manage/{token}/accept", guest(holder.token)));

export const payDeposit = (id: string) =>
  unwrap(api.POST("/api/v1/booking/appointments/{appointment_id}/pay", mine(id)));

export const getMyWaitlist = () => unwrap(api.GET("/api/v1/booking/waitlist"));

export const leaveWaitlist = (id: string) =>
  unwrap(api.DELETE("/api/v1/booking/waitlist/{entry_id}", { params: { path: { entry_id: id } } }));

// --- The agenda ----------------------------------------------------------------------------------

const agendaItem = (id: string) => ({ params: { path: { appointment_id: id } } });

export const getAgenda = (query: { start: string; days?: number; staff?: string; pro?: string }) =>
  unwrap(api.GET("/api/v1/me/agenda", { params: { query } }));

export const quickBook = (body: Schemas["QuickBookInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/agenda/appointments", { body }));

export const getAgendaAppointment = (id: string) =>
  unwrap(api.GET("/api/v1/me/agenda/appointments/{appointment_id}", agendaItem(id)));

export const confirmAppointment = (id: string) =>
  unwrap(api.POST("/api/v1/me/agenda/appointments/{appointment_id}/confirm", agendaItem(id)));

export const declineAppointment = (id: string, message: string) =>
  unwrap(
    api.POST("/api/v1/me/agenda/appointments/{appointment_id}/decline", {
      ...agendaItem(id),
      body: { message },
    }),
  );

export const proposeTime = (id: string, start: string, message: string) =>
  unwrap(
    api.POST("/api/v1/me/agenda/appointments/{appointment_id}/propose", {
      ...agendaItem(id),
      body: { start, message },
    }),
  );

export const moveAppointment = (id: string, start: string, staffId?: string | null) =>
  unwrap(
    api.POST("/api/v1/me/agenda/appointments/{appointment_id}/move", {
      ...agendaItem(id),
      body: { start, staff_id: staffId ?? null },
    }),
  );

export const completeAppointment = (id: string) =>
  unwrap(api.POST("/api/v1/me/agenda/appointments/{appointment_id}/complete", agendaItem(id)));

export const markNoShow = (id: string) =>
  unwrap(api.POST("/api/v1/me/agenda/appointments/{appointment_id}/no-show", agendaItem(id)));

export const cancelByPro = (id: string) =>
  unwrap(
    api.POST("/api/v1/me/agenda/appointments/{appointment_id}/cancel", {
      ...agendaItem(id),
      body: {},
    }),
  );

export const adviseProduct = (id: string, productId: string, note: string) =>
  unwrap(
    api.POST("/api/v1/me/agenda/appointments/{appointment_id}/advice", {
      ...agendaItem(id),
      body: { product_id: productId, note },
    }),
  );

export const addTimeOff = (body: Schemas["TimeOffInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/agenda/time-off", { body }));

export const removeTimeOff = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/agenda/time-off/{time_off_id}", {
      params: { path: { time_off_id: id } },
    }),
  );

export const getStaff = () => unwrap(api.GET("/api/v1/me/agenda/staff"));

export const addStaff = (body: Schemas["StaffInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/agenda/staff", { body }));

export const updateStaff = (id: string, body: Schemas["PatchedStaffInputRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/me/agenda/staff/{staff_id}", {
      params: { path: { staff_id: id } },
      body,
    }),
  );

export const setStaffHours = (id: string, body: Schemas["StaffHoursInputRequest"]) =>
  unwrap(
    api.PUT("/api/v1/me/agenda/staff/{staff_id}/hours", {
      params: { path: { staff_id: id } },
      body,
    }),
  );

export const addResource = (body: Schemas["ResourceInputRequest"]) =>
  unwrap(api.POST("/api/v1/me/agenda/resources", { body }));

export const removeResource = (id: string) =>
  unwrap(
    api.DELETE("/api/v1/me/agenda/resources/{resource_id}", {
      params: { path: { resource_id: id } },
    }),
  );

export const getAgendaSettings = () => unwrap(api.GET("/api/v1/me/agenda/settings"));

export const updateAgendaSettings = (body: Schemas["PatchedAgendaSettingsInputRequest"]) =>
  unwrap(api.PATCH("/api/v1/me/agenda/settings", { body }));

export const setLastMinute = (body: Schemas["LastMinuteInputRequest"]) =>
  unwrap(api.PUT("/api/v1/me/agenda/last-minute", { body }));

export const getClientRecords = (q?: string) =>
  unwrap(api.GET("/api/v1/me/agenda/clients", { params: { query: { q } } }));

export const getClientRecord = (id: string) =>
  unwrap(api.GET("/api/v1/me/agenda/clients/{record_id}", { params: { path: { record_id: id } } }));

export const updateClientRecord = (id: string, body: Schemas["PatchedClientRecordInputRequest"]) =>
  unwrap(
    api.PATCH("/api/v1/me/agenda/clients/{record_id}", {
      params: { path: { record_id: id } },
      body,
    }),
  );

export const BOOKING_QR_URL = "/api/v1/me/agenda/qr.png";
