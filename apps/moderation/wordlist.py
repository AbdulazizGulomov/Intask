# apps/moderation/wordlist.py
"""Banned-word lists for the UGC content filter (App Store Guideline 1.2).

Kept deliberately separate from the matching logic in filters.py so the lists
can be extended by anyone without touching code that has tests.

Rules for editing:
  * lowercase only — the matcher lowercases input before comparing;
  * one word or phrase per entry; a phrase matches across single spaces;
  * entries match on WORD BOUNDARIES, so "meth" does not flag "method";
  * a trailing "*" means STEM match — "хуй*" also flags "хуйня", "хуйло".
    Uzbek and Russian suffix heavily, so most entries in those lists are
    stems. Use it sparingly in English, where it over-matches easily.

A deployment can extend these without a code change via
settings.MODERATION_EXTRA_BANNED_WORDS (see filters.banned_words()).
"""

# Uzbek (Latin script). Profanity and slurs, plus the solicitation/scam
# phrasings that turn up on job listings.
UZ = [
    "jalab*",
    "qahpa*",
    "amini",
    "ko'tini",
    "kotini",
    "sik*",
    "qo'toq*",
    "qotoq*",
    "dalbayob*",
    "pidaras*",
    "haromi*",
    "tezak",
    "giyohvand*",
    "nashavand*",
    "nasvoy sotaman",
    "qurol sotaman",
    "eskort",
    "intim xizmat",
    "tungi xizmat",
    "pul yuvish",
    "soxta hujjat",
    "qalbaki hujjat",
]

# Russian. Core mat (as stems — they inflect in every direction) plus the same
# solicitation/scam categories.
RU = [
    "бля*",
    "блят*",
    "блядь*",
    "хуй*",
    "хуе*",
    "хуя*",
    "пизд*",
    "еб*",
    "заеб*",
    "мудак*",
    "гандон*",
    "пидор*",
    "сука",
    "суки",
    "шлюх*",
    "проститут*",
    "эскорт*",
    "интим услуги",
    "интим-услуги",
    "наркот*",
    "закладка",
    "закладки",
    "мефедрон",
    "оружие продам",
    "отмывание денег",
    "поддельные документы",
    "фальшивые документы",
]

# English. Plain word-boundary matching — stems over-match badly here.
EN = [
    "fuck",
    "fucking",
    "fucker",
    "motherfucker",
    "shit",
    "bullshit",
    "bitch",
    "bastard",
    "cunt",
    "asshole",
    "dickhead",
    "whore",
    "slut",
    "faggot",
    "nigger",
    "retard",
    "escort service",
    "sex work",
    "drugs for sale",
    "buy drugs",
    "cocaine",
    "heroin",
    "meth",
    "guns for sale",
    "money laundering",
    "fake passport",
    "fake documents",
    "child porn",
]

# What filters.py consumes. Order is irrelevant; duplicates are harmless.
BANNED_WORDS = UZ + RU + EN
