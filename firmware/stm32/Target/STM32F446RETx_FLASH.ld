/*
******************************************************************************
**  UniSat — STM32F446RETx linker script
**
**  Target:       STM32F446RETx (LQFP64, 512 KB Flash, 128 KB SRAM)
**  Toolchain:    GNU Tools for ARM Embedded (arm-none-eabi)
**  Entry point:  Reset_Handler (defined in startup_stm32f446retx.s)
**
**  Memory layout
**  -------------
**    FLASH  : 0x08000000 + 512 KB — code, vector table, rodata, init data image
**    RAM    : 0x20000000 + 128 KB — .data, .bss, FreeRTOS heap, main stack
**
**  Output sections
**  ---------------
**    .isr_vector    — cortex-M4 exception + IRQ vector table (must be first).
**    .text          — code + rodata (PROGBITS, read-only in flash).
**    .ARM.exidx     — exception unwind tables (required by -specs=nosys).
**    .data          — initialised globals (loaded at _sidata in flash,
**                     copied to RAM in startup before main()).
**    .bss           — zero-initialised globals (cleared in startup).
**    ._user_heap_stack — remaining SRAM kept for heap + main stack, with
**                        compile-time check that _Min_Heap_Size /
**                        _Min_Stack_Size fit.
**
**  FreeRTOS note
**  -------------
**  FreeRTOS heap_4.c allocates from its own `ucHeap[ configTOTAL_HEAP_SIZE ]`
**  in .bss; the linker-reserved heap here is for newlib-nano (_sbrk). Keep
**  both, they don't overlap.
******************************************************************************
*/

/* Entry point */
ENTRY(Reset_Handler)

/* Top of RAM (used as initial main-stack pointer by startup) */
_estack = ORIGIN(RAM) + LENGTH(RAM);    /* = 0x20020000 */

/* Minimum sizes enforced at link time */
_Min_Heap_Size  = 0x200;   /* 512 B  for newlib-nano _sbrk()               */
_Min_Stack_Size = 0x400;   /* 1024 B for the main() stack before scheduler */

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 512K
  RAM   (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
}

SECTIONS
{
  /* ---- Vector table — MUST be first, at 0x08000000 ------------------- */
  .isr_vector :
  {
    . = ALIGN(4);
    KEEP(*(.isr_vector))
    . = ALIGN(4);
  } >FLASH

  /* ---- Program code + read-only data --------------------------------- */
  .text :
  {
    . = ALIGN(4);
    *(.text)
    *(.text*)
    *(.glue_7)
    *(.glue_7t)
    *(.eh_frame)

    KEEP (*(.init))
    KEEP (*(.fini))

    . = ALIGN(4);
    _etext = .;
  } >FLASH

  .rodata :
  {
    . = ALIGN(4);
    *(.rodata)
    *(.rodata*)
    . = ALIGN(4);
  } >FLASH

  /* ---- ARM exception unwind tables (required by -specs=nosys) -------- */
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } >FLASH

  .ARM :
  {
    __exidx_start = .;
    *(.ARM.exidx*)
    __exidx_end   = .;
  } >FLASH

  /* ---- C runtime constructors / destructors -------------------------- */
  .preinit_array :
  {
    PROVIDE_HIDDEN (__preinit_array_start = .);
    KEEP (*(.preinit_array*))
    PROVIDE_HIDDEN (__preinit_array_end = .);
  } >FLASH

  .init_array :
  {
    PROVIDE_HIDDEN (__init_array_start = .);
    KEEP (*(SORT(.init_array.*)))
    KEEP (*(.init_array*))
    PROVIDE_HIDDEN (__init_array_end = .);
  } >FLASH

  .fini_array :
  {
    PROVIDE_HIDDEN (__fini_array_start = .);
    KEEP (*(SORT(.fini_array.*)))
    KEEP (*(.fini_array*))
    PROVIDE_HIDDEN (__fini_array_end = .);
  } >FLASH

  /* ---- .data : load image in flash, run copy in RAM ------------------ */
  _sidata = LOADADDR(.data);

  .data :
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data)
    *(.data*)

    . = ALIGN(4);
    _edata = .;
  } >RAM AT> FLASH

  /* ---- .bss : zero-initialised globals ------------------------------- */
  .bss :
  {
    . = ALIGN(4);
    _sbss = .;
    __bss_start__ = _sbss;
    *(.bss)
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
    __bss_end__ = _ebss;
  } >RAM

  /* ---- .noinit : preserved across warm resets ------------------------
   *
   * Variables placed here (via __attribute__((section(".noinit")))) are
   * NOT zeroed by Reset_Handler's BSS-init loop. The SRAM block keeps
   * its contents across a soft reset (NVIC_SystemReset, watchdog
   * timeout, HardFault), which lets the FDIR persistent fault log
   * survive a reboot and land in the next boot's downlink.
   *
   * The section is RAM-only (no flash load image), so the values are
   * undefined on a cold power-on — the consumer must validate with a
   * magic-number header (see fdir_persistent.c). Placing after .bss
   * keeps the zero-init sweep from touching it and avoids layout
   * churn for existing .bss symbols.
   */
  .noinit (NOLOAD) :
  {
    . = ALIGN(4);
    _snoinit = .;
    *(.noinit)
    *(.noinit.*)
    . = ALIGN(4);
    _enoinit = .;
  } >RAM

  /* ---- Heap + main stack region : everything left in RAM ------------- */
  ._user_heap_stack :
  {
    . = ALIGN(8);
    PROVIDE ( end    = . );      /* used by _sbrk() for heap start */
    PROVIDE ( _end   = . );
    . = . + _Min_Heap_Size;
    . = . + _Min_Stack_Size;
    . = ALIGN(8);
  } >RAM

  /* ---- Discard compiler/linker junk ---------------------------------- */
  /DISCARD/ :
  {
    libc.a   ( * )
    libm.a   ( * )
    libgcc.a ( * )
  }

  .ARM.attributes 0 : { *(.ARM.attributes) }
}
