/**
 * @file stm32_assert.h
 * @brief STM32 LL-driver assertion macro (no-op for release build).
 *
 * STMicroelectronics low-level drivers include this project-specific
 * header to wire `assert_param()` to whatever assertion policy the
 * user picked. UniSat builds release-mode by default so the macro is
 * a no-op; a debug build would replace this with a printf + trap.
 */
#ifndef STM32_ASSERT_H
#define STM32_ASSERT_H

#ifdef USE_FULL_ASSERT
  /* Same prototype as stm32f4xx_hal_conf.h's assert_failed so the
   * LL driver's calls link against the HAL layer's implementation. */
  void assert_failed(unsigned char *file, unsigned long line);
  #define assert_param(expr)  \
      ((expr) ? (void)0U : assert_failed((unsigned char *)__FILE__, __LINE__))
#else
  #define assert_param(expr)  ((void)0U)
#endif

#endif /* STM32_ASSERT_H */
