#include <array>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <string>
#include <fastcdr/Cdr.h>
#include <fastcdr/FastBuffer.h>
#include <fastcdr/exceptions/Exception.h>

using eprosima::fastcdr::Cdr;
#ifndef FASTCDR350_PR_HEAD
#define FASTCDR350_PR_HEAD 1
#endif
#if FASTCDR350_PR_HEAD
using eprosima::fastcdr::CdrTryConstructFlag;
#endif
using eprosima::fastcdr::CdrVersion;
using eprosima::fastcdr::FastBuffer;

static std::array<char, 4> header(uint32_t count, Cdr::Endianness endian)
{
    std::array<char, 4> bytes {};
    for (int i = 0; i < 4; ++i)
    {
        const int offset = endian == Cdr::LITTLE_ENDIANNESS ? i : (3 - i);
        bytes[i] = static_cast<char>((count >> (8 * offset)) & 0xff);
    }
    return bytes;
}

static bool rejected(uint32_t count, Cdr::Endianness endian, CdrVersion version, bool bounded)
{
    auto bytes = header(count, endian);
    FastBuffer buffer(bytes.data(), bytes.size());
    Cdr cdr(buffer, endian, version);
    std::wstring output {L"previous"};
    try
    {
#if FASTCDR350_PR_HEAD
        if (bounded)
        {
            cdr.deserialize(output, CdrTryConstructFlag::FAIL, (std::numeric_limits<uint32_t>::max)());
        }
        else
#endif
        {
            cdr.deserialize(output);
        }
        std::cout << "ACCEPT count=" << count << " endian=" << static_cast<unsigned>(endian)
                  << " version=" << static_cast<unsigned>(version) << " bounded=" << bounded
                  << " decoded_size=" << output.size() << '\n';
        return false;
    }
    catch (const eprosima::fastcdr::exception::Exception& ex)
    {
        std::cout << "REJECT count=" << count << " endian=" << static_cast<unsigned>(endian)
                  << " version=" << static_cast<unsigned>(version) << " bounded=" << bounded
                  << " reason=" << ex.what() << '\n';
        return true;
    }
}

static bool valid_roundtrip(Cdr::Endianness endian, CdrVersion version, bool bounded)
{
    std::array<char, 64> bytes {};
    FastBuffer output_buffer(bytes.data(), bytes.size());
    Cdr writer(output_buffer, endian, version);
    const std::wstring expected = L"AB";
    writer.serialize(expected);

    FastBuffer input_buffer(bytes.data(), writer.get_serialized_data_length());
    Cdr reader(input_buffer, endian, version);
    std::wstring decoded;
#if FASTCDR350_PR_HEAD
    if (bounded)
    {
        reader.deserialize(decoded, CdrTryConstructFlag::FAIL, 2);
    }
    else
#endif
    {
        reader.deserialize(decoded);
    }
    const bool equal = decoded == expected;
    std::cout << (equal ? "ROUNDTRIP_PASS" : "ROUNDTRIP_FAIL")
              << " endian=" << static_cast<unsigned>(endian)
              << " version=" << static_cast<unsigned>(version)
              << " bounded=" << bounded << '\n';
    return equal;
}

#if FASTCDR350_PR_HEAD
static bool rejected_bounded_pointer(uint32_t count, Cdr::Endianness endian, CdrVersion version)
{
    auto bytes = header(count, endian);
    FastBuffer buffer(bytes.data(), bytes.size());
    Cdr cdr(buffer, endian, version);
    wchar_t* output = nullptr;
    try
    {
        // TRIM with a zero-character destination bounds allocation to a single wchar_t.
        // This intentionally avoids triggering the unbounded pointer overload's large allocation.
        cdr.deserialize(output, CdrTryConstructFlag::TRIM, 0);
        std::cout << "ACCEPT_POINTER count=" << count << " endian=" << static_cast<unsigned>(endian)
                  << " version=" << static_cast<unsigned>(version) << '\n';
        std::free(output);
        return false;
    }
    catch (const eprosima::fastcdr::exception::Exception& ex)
    {
        std::cout << "REJECT_POINTER count=" << count << " endian=" << static_cast<unsigned>(endian)
                  << " version=" << static_cast<unsigned>(version) << " reason=" << ex.what() << '\n';
        std::free(output);
        return true;
    }
}
#endif

int main()
{
    unsigned violations = 0;
    for (auto version : {CdrVersion::XCDRv1, CdrVersion::XCDRv2})
    {
        for (auto endian : {Cdr::LITTLE_ENDIANNESS, Cdr::BIG_ENDIANNESS})
        {
#if FASTCDR350_PR_HEAD
            for (auto bounded : {false, true})
#else
            for (auto bounded : {false})
#endif
            {
                if (!valid_roundtrip(endian, version, bounded))
                {
                    ++violations;
                }
                // A four-byte buffer cannot contain 2^31 UTF-16 code units.
                if (!rejected(0x80000000u, endian, version, bounded))
                {
                    ++violations;
                }
                // Positive control: a one-character wide string needs more than its length header.
                if (!rejected(1u, endian, version, bounded))
                {
                    ++violations;
                }
            }
#if FASTCDR350_PR_HEAD
            if (!rejected_bounded_pointer(0x80000000u, endian, version))
            {
                ++violations;
            }
            if (!rejected_bounded_pointer(1u, endian, version))
            {
                ++violations;
            }
#endif
        }
    }
    std::cout << "VIOLATIONS=" << violations << '\n';
    return violations == 0 ? 0 : 1;
}
