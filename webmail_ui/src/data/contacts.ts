export type ContactGroup = "team" | "customers" | "vendors" | "personal";

export interface Contact {
  id: string;
  name: string;
  email: string;
  phone?: string;
  company?: string;
  role?: string;
  group: ContactGroup;
  notes?: string;
  pinned?: boolean;
}

export const CONTACT_GROUPS: { id: ContactGroup; label: string }[] = [
  { id: "team", label: "Team" },
  { id: "customers", label: "Customers" },
  { id: "vendors", label: "Vendors" },
  { id: "personal", label: "Personal" },
];

export const CONTACTS: Contact[] = [
  {
    id: "c-priya",
    name: "Priya Raman",
    email: "priya@psense.ai",
    phone: "+1 (415) 555-0142",
    company: "PSense.ai",
    role: "VP Product",
    group: "team",
    pinned: true,
    notes: "Direct manager — weekly 1:1 Tuesdays.",
  },
  {
    id: "c-maya",
    name: "Maya Sullivan",
    email: "maya@psense.ai",
    company: "PSense.ai",
    role: "Senior Designer",
    group: "team",
    pinned: true,
  },
  {
    id: "c-daniel",
    name: "Daniel Okafor",
    email: "daniel@psense.ai",
    company: "PSense.ai",
    role: "CEO",
    group: "team",
  },
  {
    id: "c-ines",
    name: "Ines Carvalho",
    email: "ines@psense.ai",
    company: "PSense.ai",
    role: "Design Lead",
    group: "team",
  },
  {
    id: "c-jordan",
    name: "Jordan Patel",
    email: "jordan@northwind.co",
    company: "Northwind Logistics",
    role: "Director of Ops",
    group: "customers",
    pinned: true,
    notes: "Primary champion at Northwind. Renewal Q3.",
  },
  {
    id: "c-helena",
    name: "Helena Voss",
    email: "helena.voss@northwind.com",
    company: "Northwind Logistics",
    role: "Security Lead",
    group: "customers",
  },
  {
    id: "c-marcus",
    name: "Marcus Webb",
    email: "marcus@globalretail.io",
    company: "Global Retail",
    role: "VP Engineering",
    group: "customers",
  },
  {
    id: "c-karim",
    name: "Karim Aziz",
    email: "karim@acme.io",
    company: "Acme",
    role: "Procurement",
    group: "customers",
  },
  {
    id: "c-tomas",
    name: "Tomas Berg",
    email: "tomas@globex.com",
    company: "Globex",
    role: "Customer Success",
    group: "customers",
  },
  {
    id: "c-sasha",
    name: "Sasha Lin",
    email: "sasha@cushwake.com",
    company: "Cushman & Wakefield",
    role: "Broker",
    group: "vendors",
  },
  {
    id: "c-lena",
    name: "Lena Park",
    email: "lena@auditfirm.com",
    company: "Audit Firm LLP",
    role: "Compliance",
    group: "vendors",
  },
  {
    id: "c-linear",
    name: "Linear Billing",
    email: "billing@linear.app",
    company: "Linear",
    group: "vendors",
  },
  {
    id: "c-jules",
    name: "Jules Marchetti",
    email: "jules@marchetti.studio",
    company: "Marchetti Studio",
    role: "Friend",
    group: "personal",
    pinned: true,
  },
  {
    id: "c-sam",
    name: "Sam Rivera",
    email: "sam.rivera@gmail.com",
    group: "personal",
  },
];
