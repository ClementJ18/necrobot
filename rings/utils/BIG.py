import os
import struct


def dir_to_binary(directory):
    binary_files = []
    file_count = 0
    total_size = 0

    for dir_name, _, file_list in os.walk(directory):
        for filename in file_list:
            complete_name = f"{dir_name}/{filename}"
            sage_name = complete_name.replace(f"{directory}/", "", 1)

            size = os.path.getsize(complete_name)
            binary_files.append(
                {
                    "name": sage_name,
                    "size": size,
                    "path": complete_name,
                }
            )

            file_count += 1
            total_size += size

    binary_files.sort(key=lambda x: x["name"])

    return binary_files, total_size, file_count


def pack_file(directory, file_object):
    offset = 0
    f = file_object

    #  header, charstring, 4 bytes - always BIG4 or something similiar
    header = "BIG4"
    f.write(struct.pack("4s", header.encode("utf-8")))
    offset += 4

    binary, total_size, file_count = dir_to_binary(directory)

    #  https://github.com/chipgw/openbfme/blob/master/bigreader/bigarchive.cpp
    #  /* 8 bytes for every entry + 20 at the start and end. */
    first_entry = (len(binary) * 8) + 20

    for file in binary:
        first_entry += len(file["name"]) + 1

    #  total file size, unsigned integer, 4 bytes, little endian byte order
    size = total_size + first_entry + 1
    f.write(struct.pack("<I", size))
    offset += 4

    #  number of embedded files, unsigned integer, 4 bytes, big endian byte order
    f.write(struct.pack(">I", file_count))
    offset += 4

    #   total size of index table in bytes, unsigned integer, 4 bytes, big endian byte order
    f.write(struct.pack(">I", first_entry))
    offset += 4

    raw_data = b""
    position = 1

    for file in binary:
        #   position of embedded file within BIG-file, unsigned integer, 4 bytes, big endian byte order
        #   size of embedded data, unsigned integer, 4 bytes, big endian byte order
        f.write(struct.pack(">II", first_entry + position, file["size"]))

        #   file name, cstring, ends with null byte
        name = file["name"].encode("latin-1") + b"\x00"
        f.write(struct.pack(f"{len(name)}s", name))

        with open(file["path"], "rb") as b:
            raw_data += b.read()

        position += file["size"]

    #  not sure what's this but I think we need it see:
    #  https://github.com/chipgw/openbfme/blob/master/bigreader/bigarchive.cpp
    f.write(b"L253")
    f.write(b"\0")

    #   raw file data at the positions specified in the index
    f.write(raw_data)
    f.seek(0)

    return f


def unpack_file(file):
    pass
