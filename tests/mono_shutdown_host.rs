#![no_std]
#![no_main]
use core::ffi::{c_char, c_void};
use core::panic::PanicInfo;
#[link(name = "kernel32")]
extern "system" {
    fn LoadLibraryA(path: *const c_char) -> *mut c_void;
    fn GetProcAddress(module: *mut c_void, name: *const c_char) -> *mut c_void;
    fn GetStdHandle(which: u32) -> *mut c_void;
    fn WriteFile(handle: *mut c_void, data: *const u8, size: u32, written: *mut u32, over: *mut c_void) -> i32;
    fn ExitProcess(code: u32) -> !;
    fn SetErrorMode(mode: u32) -> u32;
}
#[panic_handler]
fn panic(_: &PanicInfo) -> ! { unsafe { ExitProcess(99) } }
#[no_mangle]
pub unsafe extern "C" fn memcpy(dest: *mut c_void, src: *const c_void, n: usize) -> *mut c_void {
    let mut i = 0;
    while i < n { core::ptr::write_volatile((dest as *mut u8).add(i), core::ptr::read_volatile((src as *const u8).add(i))); i += 1; }
    dest
}
unsafe fn say(text: &[u8]) {
    let mut written = 0;
    WriteFile(GetStdHandle(-11i32 as u32), text.as_ptr(), text.len() as u32, &mut written, core::ptr::null_mut());
}
#[no_mangle]
pub unsafe extern "C" fn mainCRTStartup() -> ! {
    // This standalone process has no game, Unity scene, Steam or save access.
    SetErrorMode(3);
    let module = LoadLibraryA(b"C:\\Games\\Steam\\steamapps\\common\\Monster Prom 4 - Monster Con\\MonoBleedingEdge\\EmbedRuntime\\mono-2.0-bdwgc.dll\0".as_ptr() as _);
    if module.is_null() { ExitProcess(10); }
    let set_path: unsafe extern "C" fn(*const c_char) = core::mem::transmute(GetProcAddress(module, b"mono_set_assemblies_path\0".as_ptr() as _));
    let init: unsafe extern "C" fn(*const c_char, *const c_char) -> *mut c_void = core::mem::transmute(GetProcAddress(module, b"mono_jit_init_version\0".as_ptr() as _));
    let open: unsafe extern "C" fn(*mut c_void, *const c_char) -> *mut c_void = core::mem::transmute(GetProcAddress(module, b"mono_domain_assembly_open\0".as_ptr() as _));
    let exec: unsafe extern "C" fn(*mut c_void, *mut c_void, i32, *mut *mut c_char) -> i32 = core::mem::transmute(GetProcAddress(module, b"mono_jit_exec\0".as_ptr() as _));
    let cleanup: unsafe extern "C" fn(*mut c_void) = core::mem::transmute(GetProcAddress(module, b"mono_jit_cleanup\0".as_ptr() as _));
    set_path(b"C:\\Games\\Steam\\steamapps\\common\\Monster Prom 4 - Monster Con\\MonsterCon_Data\\Managed\0".as_ptr() as _);
    let domain = init(b"roadtrip-isolated-test\0".as_ptr() as _, b"v4.0.30319\0".as_ptr() as _);
    if domain.is_null() { ExitProcess(11); }
    let mut path = *b"D:\\Codex_Trans\\Monster-Prom-4-KR\\build\\shutdown_probe\\MonoShutdownProbe.exe\0";
    let assembly = open(domain, path.as_ptr() as _);
    if assembly.is_null() { ExitProcess(12); }
    let mut argv = [path.as_mut_ptr() as *mut c_char];
    let result = exec(domain, assembly, 1, argv.as_mut_ptr());
    say(b"BEFORE_MONO_CLEANUP\r\n");
    cleanup(domain);
    say(b"AFTER_MONO_CLEANUP\r\n");
    ExitProcess(result as u32);
}
