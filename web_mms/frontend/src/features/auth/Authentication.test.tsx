import { fireEvent,render,screen,waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { LoginPage } from "./LoginPage";
import { AppLayout } from "../../layouts/AppLayout";

test("login submits credentials and returns current user",async()=>{const user={email:"admin@example.com",display_name:"Admin",roles:["Admin"],development:false};const fetchMock=vi.fn(()=>Promise.resolve(new Response(JSON.stringify(user),{status:200,headers:{"Content-Type":"application/json"}})));vi.stubGlobal("fetch",fetchMock);const onLogin=vi.fn();render(<LoginPage onLogin={onLogin}/>);fireEvent.change(screen.getByLabelText("Email"),{target:{value:user.email}});fireEvent.change(screen.getByLabelText("Password"),{target:{value:"long-password"}});fireEvent.click(screen.getByRole("button",{name:"Sign in"}));await waitFor(()=>expect(onLogin).toHaveBeenCalledWith(user))});

test("packing navigation hides admin layout and user controls",()=>{render(<AppLayout active="Consignments" setActive={vi.fn()} user={{email:"p@example.com",display_name:"Packing User",roles:["Packing"],development:false}} onLogout={vi.fn()}><div>content</div></AppLayout>);expect(screen.queryByText("Printers")).toBeNull();expect(screen.queryByText("Users")).toBeNull();expect(screen.getByText("Print Queue")).toBeTruthy()});

test("logout action is reachable",()=>{const logout=vi.fn();render(<AppLayout active="Consignments" setActive={vi.fn()} user={{email:"a@example.com",display_name:"Admin",roles:["Admin"],development:false}} onLogout={logout}><div/></AppLayout>);fireEvent.click(screen.getByLabelText("Logout"));expect(logout).toHaveBeenCalledOnce()});
