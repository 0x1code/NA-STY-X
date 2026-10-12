_RNvCs1AhJyItm4Gv_14nastyx_message10tags_equal:
	movdqu	(%rcx), %xmm0
	movdqu	(%rdx), %xmm1
	pcmpeqb	%xmm0, %xmm1
	pmovmskb	%xmm1, %eax
	xorl	$65535, %eax
	sete	%al
	retq
