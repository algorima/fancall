"""
Prepared replies for the fan lines that idols answer the same way every time.

In 361 exchanges from real 영통팬싸 (2026-10-23 count), about 30% of fan lines
are a greeting (4%), a compliment on looks (8%), love or thanks (10%), a
goodbye (6%) or "it's my first time" (2%). Idols answer those with short set
phrases: brushing off a compliment ("아니~ 아닌데?"), thanks ("아유 고마워요"),
"또 봐요". Saying a prepared line skips the LLM and TTS, so the reply starts as
soon as the fan's turn ends. Everything else, and any line that asks something,
still goes to the LLM, since it has to answer what the fan actually said.

A request to kiss or touch also gets a prepared reply, whatever its length or
form: the trainee gets shy and changes the subject. Prompt rules alone let a
cheek-kiss description through now and then, so the LLM never sees it.

"Do you remember me?" is left to the LLM: a prepared "of course I remember"
would be a lie when the trainee has no memory of the fan.

The Korean lines follow what idols said in those calls; English and Japanese
are translations.
"""

import random
import re
from dataclasses import dataclass
from enum import Enum

from fancall.agent.quick_reaction import is_question


class FanMove(Enum):
    """Fan lines that get a prepared reply."""

    GREETING = "greeting"
    LOOKS = "looks"
    LOVE = "love"
    GOODBYE = "goodbye"
    FIRST_TIME = "first_time"
    INTIMACY = "intimacy"


@dataclass(frozen=True)
class Line:
    """One prepared reply in each language."""

    ko: str
    en: str
    ja: str


LINES: dict[FanMove, tuple[Line, ...]] = {
    FanMove.GREETING: (
        Line(
            "안녕하세요~ 잘 들려요?",
            "Hi~ Can you hear me okay?",
            "こんにちは~ 聞こえてる？",
        ),
        Line(
            "반가워요~ 잘 지냈어요?",
            "Hey~ Good to see you. How've you been?",
            "会えて嬉しい~ 元気だった？",
        ),
        Line(
            "어 안녕~ 보여요 보여요!",
            "Oh hi~ I can see you!",
            "あ、やっほー~ 見えてるよ！",
        ),
    ),
    FanMove.LOOKS: (
        Line("아니~ 아닌데?", "Aww, no way~", "いやいや、そんなことないよ~"),
        Line(
            "어 진짜요? 고마워요~",
            "Oh, really? Thank you~",
            "えっ、ほんと？ ありがとう~",
        ),
        Line(
            "진짜요~? 마음에 들어요?", "Really~? You like it?", "ほんと~？ 気に入った？"
        ),
        Line(
            "맞아요. 아, 아니에요~",
            "I know. Wait, no, I'm kidding~",
            "そうそう。あ、うそうそ~",
        ),
    ),
    FanMove.LOVE: (
        Line(
            "아 진짜요? 아유, 고마워요",
            "Oh, really? Aww, thank you",
            "えっ、ほんと？ あらら、ありがとう",
        ),
        Line("저도 사랑해요~", "I love you too~", "僕も大好きだよ~"),
        Line(
            "와, 감동이다 진짜. 고마워요",
            "Wow, I'm really touched. Thank you",
            "わあ、本当に感動した。ありがとう",
        ),
    ),
    FanMove.GOODBYE: (
        Line(
            "와줘서 너무 고마워요. 또 봐요~",
            "Thank you so much for coming. See you again~",
            "来てくれて本当にありがとう。またね~",
        ),
        Line(
            "조심히 들어가요~ 또 얘기해요~",
            "Get home safe~ Let's talk again~",
            "気をつけて帰ってね~ また話そう~",
        ),
        Line(
            "아프지 말고, 또 만나요~",
            "Stay healthy, okay? See you again~",
            "体に気をつけてね。また会おう~",
        ),
    ),
    FanMove.FIRST_TIME: (
        Line(
            "진짜요? 처음이에요? 영광이에요~",
            "Really? Your first time? I'm honored~",
            "ほんと？ 初めて？ 光栄だな~",
        ),
        Line(
            "엇 반가워요! 와줘서 고마워요",
            "Oh, nice to meet you! Thanks for coming",
            "わ、はじめまして！ 来てくれてありがとう",
        ),
    ),
    FanMove.INTIMACY: (
        Line(
            "어우, 부끄럽게 왜 그래요~ 우리 다른 얘기 해요!",
            "Whoa, you're making me blush~ Let's talk about something else!",
            "うわ、照れるじゃん~ 別の話しよ！",
        ),
        Line(
            "에이~ 그건 비밀이에요. 오늘 뭐 했어요?",
            "Hey~ That's a secret. So what did you do today?",
            "えー、それは秘密~ 今日は何してた？",
        ),
        Line(
            "아 진짜, 얼굴 빨개졌잖아요~ 다른 거 물어봐요!",
            "Oh my gosh, my face is all red now~ Ask me something else!",
            "もう、顔赤くなっちゃった~ 他のこと聞いて！",
        ),
    ),
}

# Asking for a kiss or touch, not just mentioning one ("a kissing scene")
_INTIMACY = re.compile(
    r"kiss (me|you)|make out|touch me|(키스|뽀뽀)\s?(해|하자|할래)|스킨십|キスして|チューして",
    re.I,
)

# Checked in this order: "first time" and goodbyes are more specific than greetings
_MOVES: tuple[tuple[FanMove, re.Pattern[str]], ...] = (
    (FanMove.FIRST_TIME, re.compile(r"처음|첫\s?(팬싸|영통)|first time|初めて", re.I)),
    (
        FanMove.GOODBYE,
        # 작별은 말 끝에 올 때만 ("See you, Jen. Hi" 같은 이름 오인식을 작별로 읽지 않게)
        re.compile(
            r"(잘\s?가|안녕히|빠빠|또\s?(올게|봐|만나)|다음에\s?(봐|또)|bye|see you (later|again|soon|next)|gotta go|またね|バイバイ)"
            r"[\s~!.ㅠㅜ♡]*$",
            re.I,
        ),
    ),
    (
        FanMove.LOOKS,
        re.compile(
            r"잘생|예쁘|이쁘|귀여|멋있|멋져|미남|handsome|cute|pretty|beautiful|good.?looking|かっこい|かわい",
            re.I,
        ),
    ),
    (
        FanMove.LOVE,
        re.compile(
            r"사랑|좋아해|응원|덕분|고마워|감사|love you|thank you|support you|proud of you|大好き|応援|ありがとう",
            re.I,
        ),
    ),
    (
        FanMove.GREETING,
        re.compile(
            r"^(안녕|하이|hi|hello|hey|こんにちは|やっほ)|잘\s?들려|can you hear", re.I
        ),
    ),
)

# Longer lines usually carry something specific the reply has to pick up
_MAX_WORDS = 10


def fan_move(fan_text: str) -> FanMove | None:
    """The kind of fan line if it gets a prepared reply, otherwise None."""
    text = fan_text.strip()
    if _INTIMACY.search(text):
        return FanMove.INTIMACY
    if not text or len(text.split()) > _MAX_WORDS:
        return None
    # A question needs a real answer ("Hi! What's your name?")
    if is_question(text):
        return None
    moves = [move for move, pattern in _MOVES if pattern.search(text)]
    # 말 끝의 작별은 앞의 사랑·칭찬보다 우선 ("사랑해~ 빠빠"는 작별), 처음+인사는 처음으로 본다.
    # 그 밖에 두 가지에 걸리면 ("Hi! Bye!") 무엇에 답할지 LLM에 맡긴다.
    if FanMove.GOODBYE in moves and FanMove.GREETING not in moves:
        return FanMove.GOODBYE
    if moves == [FanMove.FIRST_TIME, FanMove.GREETING]:
        return FanMove.FIRST_TIME
    return moves[0] if len(moves) == 1 else None


class FastReplies:
    """Prepared replies in the fan's language, never the same line twice in a row."""

    def __init__(self, language: str | None, rng: random.Random | None = None):
        lang = (language or "en")[:2]
        self._lang = lang if lang in {"ko", "en", "ja"} else "en"
        self._rng = rng or random.Random()
        self._last: str | None = None

    def _text(self, line: Line) -> str:
        return str(getattr(line, self._lang))

    @property
    def lines(self) -> tuple[str, ...]:
        """Every prepared line in this language."""
        return tuple(self._text(line) for lines in LINES.values() for line in lines)

    def pick(self, fan_text: str) -> str | None:
        """A prepared reply for the fan's line, or None when the LLM should answer."""
        move = fan_move(fan_text)
        if move is None:
            return None
        choices = [self._text(line) for line in LINES[move]]
        choices = [c for c in choices if c != self._last] or choices
        self._last = self._rng.choice(choices)
        return self._last
